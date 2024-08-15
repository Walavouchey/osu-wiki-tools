import os
import pathlib
import typing
import urllib

from wikitools import redirect_parser, reference_parser, errors, link_parser, article_parser
from wikitools import console
from wikitools.file_utils import exists_case_sensitive, exists_case_insensitive
from wikitools.file_utils import get_canonical_path_casing
from wikitools.file_utils import is_article


class PathType:
    """
    Additional information about an article path

    Wiki articles support redirects, while news posts don't
    News post also don't have translations
    """

    WIKI = 0
    NEWS = 1
    GITHUB = 2


class RepositoryPath(typing.NamedTuple):
    """
    Relative path from the ppy/osu-wiki root to a news post markdown file or wiki article directory
    """

    path_type: int
    path: pathlib.Path
    fragment: typing.Optional[str]


def is_fragment_only(parsed_location: urllib.parse.ParseResult):
    return parsed_location.fragment and not any((parsed_location.scheme,
        parsed_location.netloc, parsed_location.path,
        parsed_location.params, parsed_location.query))


def is_news_link(parsed_location: urllib.parse.ParseResult):
    return ((parsed_location.scheme == "http" or parsed_location.scheme == "https") and
        parsed_location.netloc == "osu.ppy.sh" and parsed_location.path.startswith("/home/news/"))


def is_github_link(parsed_location: urllib.parse.ParseResult):
    return (
        (parsed_location.scheme == "http" or parsed_location.scheme == "https")
        and parsed_location.netloc == "github.com"
        and (parsed_location.path.startswith("/ppy/osu-wiki/blob/master/") or parsed_location.path.startswith("/ppy/osu-wiki/tree/master/"))
    )


def get_repo_path(
    current_article: pathlib.Path,
    link: link_parser.Link,
    parsed_location: urllib.parse.ParseResult
) -> typing.Union[RepositoryPath, errors.LinkError, None]:
    """
    Converts a wild link of into a osu-wiki repository path with an optional fragment, if possible

    Acceptable links can be in the following formats:

    - Relative wiki link: path/to/article#optional-fragment
    - Absolute wiki link: /wiki/path/to/article#optional-fragment
    - News post link: https://osu.ppy.sh/home/news/2023-01-01-news#optional-fragment
    - Section link within current article or news post: #fragment
    """

    if is_fragment_only(parsed_location):
        path_type = PathType.NEWS if current_article.as_posix().startswith("news") else PathType.WIKI
        return RepositoryPath(path_type=path_type, path=current_article, fragment=parsed_location.fragment)

    if is_news_link(parsed_location):
        file = pathlib.Path(parsed_location.path[1:] + ".md").relative_to("home").name
        year = file.split("-")[0]
        path = pathlib.Path(f"news/{year}/{file}")
        return RepositoryPath(path_type=PathType.NEWS, path=path, fragment=parsed_location.fragment)

    if is_github_link(parsed_location):
        path = pathlib.Path("/".join(parsed_location.path.split("/")[5:]))
        return RepositoryPath(path_type=PathType.GITHUB, path=path, fragment=parsed_location.fragment)

    # some external link; don't care
    if parsed_location.scheme:
        return None

    if is_article(parsed_location.path):
        return errors.MalformedLinkError(link, "wiki links must not include the article file name")

    if parsed_location.path.startswith("/"):
        # absolute wiki link
        path = pathlib.Path(parsed_location.path[1:])
        return RepositoryPath(path_type=PathType.WIKI, path=path, fragment=parsed_location.fragment)

    # domain is non-empty, but the link is internal?
    if parsed_location.netloc:
        return errors.MalformedLinkError(link, "incorrect link structure (typo?)")

    # relative wiki link
    path = current_article / parsed_location.path
    return RepositoryPath(path_type=PathType.WIKI, path=path, fragment=parsed_location.fragment)


def resolve_redirect(
    repo_path: RepositoryPath,
    link: link_parser.Link,
    reference: typing.Optional[reference_parser.Reference],
    redirects: redirect_parser.Redirects,
    exists: typing.Callable[[pathlib.Path], bool]
) -> typing.Union[typing.Tuple[RepositoryPath, str, int, str], errors.LinkError]:
    """
    Resolves a wiki article path according to redirects.

    Returns an error if the redirect or article does not exist
    """

    redirect_source = repo_path.path.relative_to("wiki").as_posix()
    try:
        redirect_destination, redirect_line_no = redirects[redirect_source.lower()]
    except KeyError:
        return errors.LinkNotFoundError(link, reference, repo_path.path.as_posix())

    split = redirect_destination.split('#')
    path = pathlib.Path('wiki') / split[0]
    fragment = split[1] if len(split) > 1 else None

    if not fragment:
        # the original link's section needs to be preserved if the redirect doesn't specify one.
        # conversely, if a redirect specifies a section, it always takes priority
        fragment = repo_path.fragment

    target_path = RepositoryPath(path_type=repo_path.path_type, path=path, fragment=fragment)

    if not exists(target_path.path):
        return errors.BrokenRedirectError(link, redirect_source, redirect_line_no, redirect_destination)

    return target_path, redirect_source, redirect_line_no, redirect_destination


def check_link(
    article: article_parser.Article, link: link_parser.Link,
    redirects: redirect_parser.Redirects, references: reference_parser.References,
    all_articles: typing.Dict[str, article_parser.Article],
    case_sensitive: bool = False
) -> typing.Optional[errors.LinkError]:
    """
    Verifies that the link is valid:
        - External links are always assumed valid, since we can't just issue HTTP requests left and right
        - For Markdown references, there exists a dereferencing line with [reference_name]: /lo/ca/ti/on
        - Direct internal links, as well as redirects, must point to existing article files
        - Relative links are parsed under the assumption that they are located inside the current article's directory
    """

    if case_sensitive:
        exists = exists_case_sensitive
    else:
        exists = exists_case_insensitive

    reference = link.resolve(references)
    if reference is None and link.is_reference:
        return errors.MissingReferenceError(link)

    current_article_path = pathlib.Path(article.path)
    if current_article_path.as_posix().startswith("wiki"):
        current_article_path = pathlib.Path(os.path.dirname(current_article_path))

    repo_path = get_repo_path(current_article_path, link, reference.parsed_location if reference else link.parsed_location)

    if isinstance(repo_path, errors.LinkError):
        return repo_path
    elif repo_path is None:
        return None

    # github gives a 404 when the casing is wrong
    if repo_path.path_type == PathType.GITHUB:
        exists = exists_case_sensitive

    redirected = False
    if not exists(repo_path.path):
        # if the article doesn't exist, check if it has a redirect
        if repo_path.path_type == PathType.NEWS or repo_path.path_type == PathType.GITHUB:
            # except news and github links don't support redirects
            return errors.LinkNotFoundError(link, reference, repo_path.path.as_posix())

        redirect_result = resolve_redirect(repo_path, link, reference, redirects, exists)
        if isinstance(redirect_result, errors.LinkError):
            return redirect_result
        repo_path, redirect_source, redirect_line_no, redirect_destination = redirect_result
        redirected = True

    # link to an article in general, article exists -> good
    if not repo_path.fragment:
        return None

    target_path = repo_path.path
    if os.name != 'nt' and not case_sensitive:
        target_path = get_canonical_path_casing(target_path)

    # link to a section
    match repo_path.path_type:
        case PathType.GITHUB:
            # github links can either be directories or files
            # but section links are only relevant for markdown files
            if repo_path.path.suffix == ".md":
                raw_path = target_path.as_posix()
                if raw_path not in all_articles:
                    # this is safe to do since the caller iterates over a copy of all_articles -> we can modify it as we wish
                    all_articles[raw_path] = article_parser.parse(target_path)

                target_article = all_articles[raw_path]

                if repo_path.fragment not in target_article.identifiers:
                    # collect some additional metadata before reporting
                    translation_outdated = False
                    if repo_path.path.name != "en.md": translation_outdated = target_article.front_matter.get('outdated_translation', False)

                    return errors.MissingIdentifierError(link, raw_path, repo_path.fragment, False, translation_outdated)
        case PathType.NEWS:
            # always a file path
            raw_path = target_path.as_posix()
            if raw_path not in all_articles:
                all_articles[raw_path] = article_parser.parse(target_path)
            target_article = all_articles[raw_path]

            if repo_path.fragment not in target_article.identifiers:
                return errors.MissingIdentifierError(link, raw_path, repo_path.fragment, False, False)
        case PathType.WIKI:
            # directory -> need to find the target article; it could be a translation
            # XXX(TicClick): this part assumes there is always an English version of the article in a folder
            target_file = target_path / article.filename
            translation = target_file # verified to be the case later
            no_translation_available = article.filename != 'en.md' and not target_file.is_file()

            if no_translation_available:
                target_file = target_path / 'en.md'

            raw_path = target_file.as_posix()
            if raw_path not in all_articles:
                # this is safe to do since the caller iterates over a copy of all_articles -> we can modify it as we wish
                all_articles[raw_path] = article_parser.parse(target_file)

            target_article = all_articles[raw_path]

            if repo_path.fragment not in target_article.identifiers:
                # collect some additional metadata before reporting
                translation_outdated = False
                if not no_translation_available:
                    raw_path_translation = translation.as_posix()
                    if raw_path_translation not in all_articles:
                        # this is safe to do since the caller iterates over a copy of all_articles -> we can modify it as we wish
                        all_articles[raw_path_translation] = article_parser.parse(translation)
                    translation_outdated = all_articles[raw_path_translation].front_matter.get('outdated_translation', False)

                # even an empty fragment in a redirect will take priority over the original link,
                # so it's enough to just check for "#"
                if redirected and "#" in redirect_destination:
                    return errors.BrokenRedirectIdentifierError(
                        link=link,
                        resolved_location=redirect_source,
                        redirect_lineno=redirect_line_no,
                        redirect_destination=redirect_destination,
                        path=raw_path,
                        identifier=repo_path.fragment,
                        no_translation_available=no_translation_available,
                        translation_outdated=translation_outdated
                    )

                return errors.MissingIdentifierError(link, raw_path, repo_path.fragment, no_translation_available, translation_outdated)

    return None


def check_article(
    article: article_parser.Article, redirects: redirect_parser.Redirects,
    all_articles: typing.Dict[str, article_parser.Article],
    case_sensitive: bool = False
) -> typing.Dict[int, typing.List[errors.LinkError]]:
    """
    Try resolving links in the article to other articles or files.
    """

    errors = {}
    for lineno, line in article.lines.items():
        local_errors = [
            errors for errors in (
                check_link(article, link, redirects, article.references, all_articles, case_sensitive)
                for link in line.links
            )
            if errors
        ]
        if local_errors:
            errors[lineno] = local_errors

    return errors
