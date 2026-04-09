#!/usr/bin/env python3
import random
import re
import signal
import subprocess
import sys
import time
from collections import defaultdict

COMMITS = [
    "63898fc98b2057",
    "85014bd4591d",
]

TARGET_TEST = (
    "tests/stockfish/test_models.py::"
    "TestStockfish::test_get_best_move_remaining_time_first_move"
)

ITERATIONS = 5000

# Change this if you want a different pytest command.
PYTEST_CMD = ["pytest", "-vv"]

RESULT_RE = re.compile(
    re.escape(TARGET_TEST) + r"\s+(PASSED|FAILED|ERROR|SKIPPED|XPASS|XFAIL)\b"
)


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def get_current_ref() -> str:
    # symbolic-ref gives branch name when on a branch; falls back to HEAD sha otherwise
    branch = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        text=True,
        capture_output=True,
    )
    if branch.returncode == 0:
        return branch.stdout.strip()

    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    )
    return sha.stdout.strip()


def ensure_clean_worktree():
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=True,
    )
    if status.stdout.strip():
        print("Refusing to run: working tree is not clean.", file=sys.stderr)
        print("Commit or stash your changes first.", file=sys.stderr)
        sys.exit(1)


def checkout(commit: str):
    run(["git", "checkout", "-q", commit])


def terminate_process_tree(proc: subprocess.Popen):
    if proc.poll() is not None:
        return

    try:
        # Start by interrupting the whole process group.
        os_killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass

    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os_killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def os_killpg(pid: int, sig: int):
    import os
    os.killpg(pid, sig)


def run_one_iteration(commit: str):
    checkout(commit)

    # New process group so we can kill pytest and any children cleanly.
    proc = subprocess.Popen(
        PYTEST_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=__import__("os").setsid,
    )

    seen_result = None

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")

            m = RESULT_RE.search(line)
            if m:
                seen_result = m.group(1)
                terminate_process_tree(proc)
                break

        # Drain a tiny bit in case process is already exiting.
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            terminate_process_tree(proc)

    finally:
        if proc.poll() is None:
            terminate_process_tree(proc)

    return seen_result


def main():
    ensure_clean_worktree()
    original_ref = get_current_ref()

    tallies = {
        commit: defaultdict(int)
        for commit in COMMITS
    }

    print(f"Original ref: {original_ref}")
    print(f"Running {ITERATIONS} iterations")
    print()

    start = time.time()

    try:
        for i in range(1, ITERATIONS + 1):
            commit = random.choice(COMMITS)
            print("=" * 80)
            print(f"Iteration {i}/{ITERATIONS} | commit {commit}")
            print("=" * 80)

            result = run_one_iteration(commit)

            if result is None:
                tallies[commit]["NO_RESULT"] += 1
                print(f"\n[iteration {i}] No target-test result seen.\n")
            else:
                tallies[commit][result] += 1
                print(f"\n[iteration {i}] {commit} -> {result}\n")
            print(f"tallies for commit {commit}, passed: {tallies[commit]['PASSED']}, failed: {tallies[commit]['FAILED']}")

    finally:
        print("\nRestoring original ref...")
        checkout(original_ref)

    elapsed = time.time() - start

    print("\n" + "#" * 80)
    print("FINAL RESULTS")
    print("#" * 80)
    print(f"Elapsed: {elapsed:.1f}s\n")

    for commit in COMMITS:
        t = tallies[commit]
        total = sum(t.values())
        passed = t["PASSED"]
        failed = t["FAILED"]
        error = t["ERROR"]
        skipped = t["SKIPPED"]
        xpass = t["XPASS"]
        xfail = t["XFAIL"]
        no_result = t["NO_RESULT"]

        pass_rate = (passed / total * 100) if total else 0.0
        fail_rate = (failed / total * 100) if total else 0.0

        print(f"Commit: {commit}")
        print(f"  Total     : {total}")
        print(f"  PASSED    : {passed}")
        print(f"  FAILED    : {failed}")
        print(f"  ERROR     : {error}")
        print(f"  SKIPPED   : {skipped}")
        print(f"  XPASS     : {xpass}")
        print(f"  XFAIL     : {xfail}")
        print(f"  NO_RESULT : {no_result}")
        print(f"  Pass rate : {pass_rate:.2f}%")
        print(f"  Fail rate : {fail_rate:.2f}%")
        print()


if __name__ == "__main__":
    main()