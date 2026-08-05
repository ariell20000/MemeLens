import json
import subprocess
import sys


def main() -> None:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})

    if tool_input.get("status") != "completed":
        return

    repo_dir = payload.get("cwd", ".")
    task_id = tool_input.get("taskId", "?")

    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repo_dir
    )
    if staged.returncode == 0:
        print(f"[auto-commit] Task {task_id} completed, no file changes to commit.")
        return

    message = f"Complete task #{task_id}\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
    subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, check=True)
    print(f"[auto-commit] Committed changes for task {task_id}.")

    push = subprocess.run(["git", "push"], cwd=repo_dir)
    if push.returncode != 0:
        push = subprocess.run(
            ["git", "push", "-u", "origin", "HEAD"], cwd=repo_dir
        )
    if push.returncode == 0:
        print(f"[auto-commit] Pushed changes for task {task_id}.")
    else:
        print(f"[auto-commit] WARNING: push failed for task {task_id}.")


if __name__ == "__main__":
    main()
