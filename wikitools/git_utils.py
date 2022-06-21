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
    res = git("diff", "--diff-filter=d", "--name-only", f"{base_commit}^", "--", *file_paths)
    return res.splitlines()
