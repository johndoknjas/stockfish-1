#!/usr/bin/env python3
import subprocess
from time import sleep
from typing import Optional


def run_trial() -> bool:
    """
    Starts a fresh global `stockfish` process, sends the requested UCI commands,
    reads output from the final `go wtime 1000 btime 1000`, and returns True
    iff the resulting bestmove is `c2c3`.
    """
    proc = subprocess.Popen(
        ["stockfish"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None

    def send(cmd: str) -> None:
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    def read_until(token: str) -> list[str]:
        lines: list[str] = []
        while True:
            line = proc.stdout.readline()
            if line == "":
                raise RuntimeError(f"Stockfish exited before emitting {token!r}")
            line = line.rstrip("\n")
            lines.append(line)
            if line.startswith(token):
                return lines

    try:
        # sleep(0.5)
        send("uci")
        read_until("uciok")

        send("isready")
        read_until("readyok")

        # First command
        send("go wtime 1000")
        read_until("bestmove")

        # send("isready")
        # read_until("readyok")

        # Second command
        send("go btime 1000")
        read_until("bestmove")

        # send("isready")
        # read_until("readyok")

        # Third command: capture this output
        send("go wtime 1000 btime 1000")
        final_output = read_until("bestmove")

        bestmove_line = final_output[-1]
        parts = bestmove_line.split()
        bestmove: Optional[str] = parts[1] if len(parts) >= 2 else None

        return bestmove == "c2c3"

    finally:
        try:
            send("quit")
        except Exception:
            pass
        proc.kill()
        proc.wait()


def main() -> None:
    trials = 100
    c2c3_count = 0

    for i in range(1, trials + 1):
        matched = run_trial()
        if matched:
            c2c3_count += 1
        print(f"trial {i}/{trials}: c2c3_count={c2c3_count}")

    print()
    print(f"final count: {c2c3_count} / {trials}")


if __name__ == "__main__":
    main()
