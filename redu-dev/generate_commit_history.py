"""
Generate a history of commits and their diff into a JSON file saved on cwd.

JSON structure:

{
    "1": {
        "commit_hash": "2631e5...",
        "commit_date": "1791400110",
        "commit_message": "Initial commit...",
        "commit_diff": "..."
    },

    "2": ...
}
"""
import json
import subprocess
import sys
from pathlib import Path


# Safe terminal encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Constants
CWD = Path.cwd()
OUTPUT_FILE = CWD / "commit_history.json"


def run_git(args: list[str], check: bool = True) -> str:
    """Execute a git command and return stripped stdout with utf-8 decoding."""
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )
        return proc.stdout.strip()
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else f"Exit code {e.returncode}"
        raise RuntimeError(f"Git command failed ('git {' '.join(args)}'): {err_msg}") from e
    except FileNotFoundError as e:
        raise RuntimeError("git executable not found in PATH.") from e


def generate_commit_history(
    starting_hash: str | None = None,
    last_hash: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """Collect git commit history and diffs between starting and last commits, saving to JSON."""
    output_target = output_path or OUTPUT_FILE

    # Validate that cwd is inside a git repository
    try:
        run_git(["status"])
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve last commit reference (defaults to HEAD)
    last_ref = last_hash.strip() if last_hash and last_hash.strip() else "HEAD"
    try:
        resolved_last = run_git(["rev-parse", last_ref])
    except RuntimeError as e:
        print(f"Error: Could not resolve last commit '{last_ref}': {e}", file=sys.stderr)
        sys.exit(1)

    # Retrieve all commits leading up to resolved_last in chronological order (oldest -> newest)
    try:
        rev_output = run_git(["rev-list", "--reverse", resolved_last])
        all_commits = [c.strip() for c in rev_output.splitlines() if c.strip()]
    except RuntimeError as e:
        print(f"Error retrieving commit list: {e}", file=sys.stderr)
        sys.exit(1)

    if not all_commits:
        print("Error: No commits found in repository.", file=sys.stderr)
        sys.exit(1)

    # Resolve starting commit reference (defaults to the initial commit)
    if starting_hash and starting_hash.strip():
        start_ref = starting_hash.strip()
        try:
            resolved_start = run_git(["rev-parse", start_ref])
        except RuntimeError as e:
            print(f"Error: Could not resolve starting commit '{start_ref}': {e}", file=sys.stderr)
            sys.exit(1)

        if resolved_start not in all_commits:
            print(
                f"Error: Starting commit '{start_ref}' ({resolved_start}) "
                f"is not an ancestor of last commit '{last_ref}' ({resolved_last}).",
                file=sys.stderr,
            )
            sys.exit(1)

        start_index = all_commits.index(resolved_start)
        selected_commits = all_commits[start_index:]
    else:
        selected_commits = all_commits

    total = len(selected_commits)
    print(f"\nProcessing {total} commit(s) from {selected_commits[0][:7]} to {selected_commits[-1][:7]}...\n")

    history: dict[str, dict[str, str]] = {}

    for idx, commit_hash in enumerate(selected_commits, start=1):
        short_hash = commit_hash[:7]
        print(f"[{idx}/{total}] Fetching commit {short_hash}...")

        # Commit timestamp (seconds since epoch)
        commit_date = run_git(["show", "-s", "--format=%ct", commit_hash])

        # Full commit message
        commit_message = run_git(["show", "-s", "--format=%B", commit_hash])

        # Commit diff
        commit_diff = run_git(["show", "--format=", commit_hash])

        history[str(idx)] = {
            "commit_hash": commit_hash,
            "commit_date": commit_date,
            "commit_message": commit_message,
            "commit_diff": commit_diff,
        }

    # Write output JSON to disk
    try:
        with open(output_target, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully generated commit history with {total} commit(s):")
        print(f"Saved to: {output_target.resolve()}\n")
    except OSError as e:
        print(f"Error saving JSON to '{output_target}': {e}", file=sys.stderr)
        sys.exit(1)

    return output_target


def main() -> None:
    """CLI entry point."""
    # Allow command-line arguments: python generate_commit_history.py [START] [LAST]
    if len(sys.argv) > 1:
        starting_input = sys.argv[1]
        last_input = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        starting_input = input("Starting commit hash (empty to auto select first commit: ").strip()
        last_input = input("Last commit hash (empty to auto select last commit): ").strip()

    generate_commit_history(
        starting_hash=starting_input or None,
        last_hash=last_input or None,
    )


if __name__ == "__main__":
    main()
