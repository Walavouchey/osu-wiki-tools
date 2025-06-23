import subprocess as sp


def git(*args, expected_code=0):
    cmd = ["git"] + list(map(str, args))
    proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    out, err = proc.communicate()
    out = out.decode("utf-8") if out else ""
    err = err.decode("utf-8") if err else ""
    if proc.returncode != expected_code:
        raise RuntimeError(
            "{} failed:\n"
            "- exit code: {}\n"
            "- stdout: {!r}\n"
            "- stderr: {!r}\n".format(
                cmd, proc.returncode, out, err
            )
        )
    return out


def git_diff(*file_paths, base_commit=""):
    res = git("diff", "--diff-filter=d", "--name-only", base_commit, "--", *file_paths)
    return res.splitlines()


def get_first_branch_commit():
    """
    Gets the first commit of the current branch where it diverges from master.

    Returns None if already on master, or if the feature branch is already merged into master

    If the current branch is more up to date with upstream master than local master,
    an even earlier commit will be returned. This can happen when checking out a PR
    branch; update local master with upstream if so.
    """

    res = git("log", "master..", "--pretty=format:%H").splitlines()
    return res[-1] if res else None
