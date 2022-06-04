#!/usr/bin/env python3

import subprocess
import sys
import os


def print_usage_and_exit():
    print(f"""Usage: {sys.argv[0]} [options]

options:
    -i --index index    Specify which commit in this branch
                        since master to use for outdating.
    -c --commit hash    Specify commit to use for outdating
                        by commit hash.
    -h --help           Print this message and exit.

Omitting arguments is equivalent to -i 1""")
    sys.exit(0)


def red(s):  # important
    return f"\x1b[31m{s}\x1b[0m" if sys.stdout.isatty() else s


def green(s):  # info
    return f"\x1b[32m{s}\x1b[0m" if sys.stdout.isatty() else s


def yellow(s):  # debug
    return f"\x1b[33m{s}\x1b[0m" if sys.stdout.isatty() else s


def blue(s):  # command run
    return f"\x1b[34m{s}\x1b[0m" if sys.stdout.isatty() else s


def error(msg):
    print(red(msg))
    sys.exit(1)


def shell(cmd):
    result = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8")


def print_and_run(cmd):
    print(blue(cmd))
    subprocess.run(cmd.split(" "))


if len(sys.argv) > 1 and ("-h" in sys.argv[1] or "--help" in sys.argv[1]):
    print_usage_and_exit()

branch = shell("git branch --show-current").strip()

if not branch or "master" in branch:
    error("Must be checked out on a feature branch (git checkout <branch_name>)")

log = shell(f"git log {branch} ^master --reverse")

commits = [line.split(" ")[1] for line in log.split("\n") if "commit" in line]
commit = ""
index = 0

if len(commits) < 1:
    error(f"No new commits on branch {branch} since master")

translations = [file for file in os.listdir(".") if ".md" in file and "en.md" not in file]

if "en.md" not in os.listdir("."):
    error("No English article found (en.md)! Are you in the right folder?")

if len(translations) < 1:
    error("No translations found! Are you in the right folder?")

log_EN = shell(f"git log {branch} ^master --reverse en.md")

commits_EN = [line.split(" ")[1] for line in log_EN.split("\n") if "commit" in line]

if len(log_EN) < 1:
    error("No new commits on en.md on this branch; there is no need to outdate.")

if len(sys.argv) > 1 and ("-c" in sys.argv[1] or "--commit" in sys.argv[1]):
    if len(sys.argv) < 3:
        print_usage_and_exit()

    log = shell(f"git log {sys.argv[2]} ^master -n 1")
    specific_commit = [line.split(" ")[1] for line in log.split("\n") if "commit" in line]
    if len(specific_commit) < 1:
        error(f"Specified commit \"{sys.argv[2]}\" not found")
    commit = specific_commit[0]
    for c in commits:
        if c == commit:
            break
        index += 1
elif len(sys.argv) > 1 and ("-i" in sys.argv[1] or "--index" in sys.argv[1]):
    if len(sys.argv) < 3:
        print_usage_and_exit()
    try:
        index = int(sys.argv[2]) - 1 if len(sys.argv) > 1 else 0
    except Exception:
        print_usage_and_exit()
    if index < 0 or index >= len(commits):
        error(f"Selection index out of range ({len(commits)} since master)")
    commit = commits[index]
elif len(sys.argv) > 1:
    print_usage_and_exit()
else:
    index = 0
    commit = commits[index]

files_edited = []
for filename in translations:
    linenumber = 0

    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
        lines = content.split("\n")
        in_yaml = False
        exited_yaml = False
        yaml_start = 0
        yaml_end = 0
        outdated = False
        has_commit_hash = False

        for line in lines:
            linenumber += 1
            if "#" in line:
                print(yellow(f"{filename}, line {linenumber}: Found heading, ending search"))
                break
            if "---" in line:
                if not exited_yaml and not in_yaml:
                    print(yellow(f"{filename}, line {linenumber}: Found start of front matter"))
                    in_yaml = True
                    yaml_start = linenumber
                elif in_yaml and not exited_yaml:
                    print(yellow(f"{filename}, line {linenumber}: Found end of front matter"))
                    exited_yaml = True
                    in_yaml = False
                    yaml_end = linenumber
                else:
                    error(f"Logic error (impossible): {filename}")
            if not in_yaml:
                continue
            if "outdated: true" in line:
                outdated = True
            if "outdated_since: true" in line:
                has_commit_hash = True

        if not exited_yaml:  # no front matter: insert markers
            print(yellow(f"{filename}: No front matter found, outdating..."))
            new_content = f"---\noutdated: true\noutdated_since: {commit}\n---\n\n" + content
            with open(filename, "w", encoding="utf-8") as writer:
                writer.write(new_content)
            files_edited.append(filename)
            continue

        if in_yaml and not exited_yaml:
            error(f"Invalid yaml formatting in {filename}")

        if not in_yaml and exited_yaml:  # front matter found
            if outdated or has_commit_hash:  # only insert if not outdated
                print(yellow(f"{filename}: Front matter found with outdated marker{'s' if outdated and has_commit_hash else ''}"))
                continue
            print(yellow(f"{filename}: Front matter found but no outdated markers, outdating..."))

            old_front_matter = "\n".join(lines[yaml_start:yaml_end])
            new_front_matter = f"---\noutdated: true\noutdated_since: {commit}\n" + old_front_matter

            print(yellow(f"Old front matter:\n{old_front_matter}\nNew front matter:\n{new_front_matter}"))

            if not new_front_matter.startswith("---") or not new_front_matter.endswith("---"):
                error(f"Logic error: {filename}")

            new_content = new_front_matter + "\n" + content[content.find("---", 4) + 4:]
            with open(filename, "w", encoding="utf-8") as writer:
                writer.write(new_content)
            files_edited.append(filename)


if len(files_edited) < 1:
    error("No translations needed outdating")

print()
print_and_run("git --no-pager diff")
print()

print(green(f"Commit used for outdated_since (commit #{index + 1} on this branch since master):"))
print_and_run(f"git --no-pager log {commit} -n 1")
print()

print_and_run(f"git add {' '.join(files_edited)}")
print(green(f"\nFiles staged: {', '.join(files_edited)}"))
print(red("Please check the above diff before committing."))
