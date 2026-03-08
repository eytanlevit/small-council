"""Tmux session management for long-running Small Council queries.

Ports the bash scripts (council-tmux-start.sh, council-tmux-wait.sh,
council-tmux-status.sh, council-tmux-cleanup.sh) into Python so the
CLI can manage tmux sessions without external shell scripts.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_tmux() -> str:
    """Return the path to tmux or exit with an error."""
    tmux = shutil.which("tmux")
    if tmux is None:
        print("ERROR: tmux is not installed or not on PATH", file=sys.stderr)
        sys.exit(1)
    return tmux


def _tmux(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run a tmux command and return the CompletedProcess."""
    tmux = _require_tmux()
    return subprocess.run(
        [tmux, *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _file_size(path: str) -> int:
    """Return file size in bytes, or 0 if the file doesn't exist."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _load_api_key() -> str:
    """Resolve the OpenRouter API key.

    Priority:
    1. OPENROUTER_API_KEY env var (already set)
    2. ~/.small-council.yaml  (api_key field)
    3. .env in CWD via python-dotenv
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    # Try ~/.small-council.yaml
    yaml_path = Path.home() / ".small-council.yaml"
    if yaml_path.exists():
        try:
            import yaml  # already a project dependency

            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
            if data.get("api_key"):
                return data["api_key"]
        except Exception:
            pass

    # Try .env in CWD via python-dotenv
    try:
        from dotenv import load_dotenv

        load_dotenv()
        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            return key
    except Exception:
        pass

    print(
        "ERROR: OPENROUTER_API_KEY not set. "
        "Export it as an environment variable or add api_key to ~/.small-council.yaml",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def start(
    prompt: str,
    files: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Start a Small Council session in a detached tmux window.

    Replicates council-tmux-start.sh behavior:
    - Generates unique session ID: council-{timestamp}-{pid}
    - Writes prompt, file list, and API key to temp files
    - Creates a wrapper bash script that runs small-council
    - Starts a tmux session running the wrapper
    - Returns JSON dict with session info
    """
    _require_tmux()

    api_key = _load_api_key()

    session_id = f"council-{int(time.time())}-{os.getpid()}"
    output_file = f"/tmp/{session_id}.out"
    done_file = f"/tmp/{session_id}.done"
    pid_file = f"/tmp/{session_id}.pid"
    error_file = f"/tmp/{session_id}.err"

    # Write prompt to temp file (avoids shell interpretation)
    prompt_tmpfile = f"/tmp/{session_id}-prompt.txt"
    Path(prompt_tmpfile).write_text(prompt)

    # Write file list (one per line)
    files_tmpfile = f"/tmp/{session_id}-files.txt"
    if files:
        Path(files_tmpfile).write_text("\n".join(files) + "\n")
    else:
        Path(files_tmpfile).write_text("")

    # Write API key with restricted permissions
    apikey_tmpfile = f"/tmp/{session_id}-apikey"
    Path(apikey_tmpfile).write_text(api_key)
    os.chmod(apikey_tmpfile, stat.S_IRUSR | stat.S_IWUSR)  # 600

    # Create wrapper script
    wrapper_script = f"/tmp/{session_id}-wrapper.sh"
    Path(wrapper_script).write_text(
        '#!/bin/bash\n'
        'OUTPUT_FILE="$1"\n'
        'DONE_FILE="$2"\n'
        'PID_FILE="$3"\n'
        'ERROR_FILE="$4"\n'
        'PROMPT_TMPFILE="$5"\n'
        'FILES_TMPFILE="$6"\n'
        'APIKEY_TMPFILE="$7"\n'
        '\n'
        '# Record our PID\n'
        'echo $$ > "$PID_FILE"\n'
        '\n'
        '# Load API key from file\n'
        'export OPENROUTER_API_KEY="$(cat "$APIKEY_TMPFILE")"\n'
        '\n'
        '# Build command array\n'
        'CMD=(small-council -a)\n'
        '\n'
        '# Add file arguments\n'
        'while IFS= read -r file; do\n'
        '    [[ -n "$file" ]] && CMD+=(-f "$file")\n'
        'done < "$FILES_TMPFILE"\n'
        '\n'
        '# Add the prompt\n'
        'CMD+=("$(cat "$PROMPT_TMPFILE")")\n'
        '\n'
        '# Run council, capture output\n'
        '{\n'
        '    "${CMD[@]}" 2>&1\n'
        '    EXIT_CODE=$?\n'
        '    if [[ $EXIT_CODE -ne 0 ]]; then\n'
        '        echo "EXIT_CODE=$EXIT_CODE" > "$ERROR_FILE"\n'
        '    fi\n'
        '} | tee "$OUTPUT_FILE"\n'
        '\n'
        '# Clean up API key file\n'
        'rm -f "$APIKEY_TMPFILE"\n'
        '\n'
        '# Signal completion\n'
        "date '+%Y-%m-%d %H:%M:%S' > \"$DONE_FILE\"\n"
        'echo "COMPLETED" >> "$DONE_FILE"\n'
    )
    os.chmod(wrapper_script, 0o755)

    # Start tmux session
    _tmux(
        "new-session", "-d", "-s", session_id,
        wrapper_script,
        output_file, done_file, pid_file, error_file,
        prompt_tmpfile, files_tmpfile, apikey_tmpfile,
    )

    info = {
        "session": session_id,
        "output": output_file,
        "done": done_file,
        "pid_file": pid_file,
        "error_file": error_file,
    }

    print(json.dumps(info, indent=2))
    return info


# ---------------------------------------------------------------------------
# wait
# ---------------------------------------------------------------------------

def wait(
    session_id: str,
    timeout: int = 1800,
    poll_interval: int = 10,
) -> None:
    """Wait for a Small Council tmux session to complete.

    Replicates council-tmux-wait.sh behavior.
    Exit codes: 0=completed, 2=timeout/error.
    """
    _require_tmux()

    output_file = f"/tmp/{session_id}.out"
    done_file = f"/tmp/{session_id}.done"
    error_file = f"/tmp/{session_id}.err"

    # Check if session exists
    result = _tmux("has-session", "-t", session_id)
    session_exists = result.returncode == 0

    if not session_exists:
        # Session gone -- check if it completed
        if os.path.isfile(done_file):
            print("=== Small Council Response ===")
            try:
                print(Path(output_file).read_text())
            except FileNotFoundError:
                print("(no output)")
            sys.exit(0)
        else:
            print(
                f"ERROR: Session '{session_id}' not found and no completion marker",
                file=sys.stderr,
            )
            sys.exit(2)

    # Poll until completion or timeout
    start_time = time.time()
    while True:
        if os.path.isfile(done_file):
            print("=== Small Council Response ===")
            try:
                print(Path(output_file).read_text())
            except FileNotFoundError:
                print("(no output)")

            if os.path.isfile(error_file):
                print()
                print("=== Warning: Process exited with error ===")
                print(Path(error_file).read_text())

            # Kill tmux session if still alive
            _tmux("kill-session", "-t", session_id)
            sys.exit(0)

        elapsed = int(time.time() - start_time)
        if elapsed >= timeout:
            print(
                f"TIMEOUT: Small Council still running after {timeout}s",
                file=sys.stderr,
            )
            print(f"Session: {session_id}", file=sys.stderr)
            print("Partial output:", file=sys.stderr)
            try:
                lines = Path(output_file).read_text().splitlines()
                for line in lines[-50:]:
                    print(line)
            except FileNotFoundError:
                print("(no output yet)")
            sys.exit(2)

        remaining = timeout - elapsed
        output_size = _file_size(output_file)
        print(
            f"RUNNING: Session {session_id} active "
            f"({elapsed}s elapsed, {remaining}s remaining, {output_size} bytes output)"
        )

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status(
    session_id: Optional[str] = None,
    list_all: bool = False,
) -> None:
    """Check status of Small Council tmux sessions.

    Replicates council-tmux-status.sh behavior.
    Exit codes: 0=found/completed, 1=running, 2=not found.
    """
    _require_tmux()

    if list_all:
        print("=== Active Small Council Sessions ===")
        result = _tmux("list-sessions")
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                if line.startswith("council-"):
                    print(line)
            # Check if any matched
            if not any(
                line.startswith("council-")
                for line in result.stdout.strip().splitlines()
            ):
                print("(none)")
        else:
            print("(none)")

        print()
        print("=== Completed Sessions (output files) ===")
        import glob

        done_files = sorted(glob.glob("/tmp/council-*.done"))
        if done_files:
            for f in done_files[:20]:
                sz = _file_size(f)
                print(f"  {f}  ({sz} bytes)")
        else:
            print("(none)")
        sys.exit(0)

    if not session_id:
        print(
            "Usage: small-council tmux status <session_id> | --list",
            file=sys.stderr,
        )
        sys.exit(2)

    output_file = f"/tmp/{session_id}.out"
    done_file = f"/tmp/{session_id}.done"
    pid_file = f"/tmp/{session_id}.pid"
    error_file = f"/tmp/{session_id}.err"

    # Check completion first
    if os.path.isfile(done_file):
        completion_time = ""
        try:
            completion_time = Path(done_file).read_text().splitlines()[0]
        except Exception:
            pass
        output_size = _file_size(output_file)

        print("Status: COMPLETED")
        print(f"Completed at: {completion_time}")
        print(f"Output file: {output_file} ({output_size} bytes)")

        if os.path.isfile(error_file):
            print(f"Warning: Process had errors (see {error_file})")

        sys.exit(0)

    # Check if session exists
    result = _tmux("has-session", "-t", session_id)
    if result.returncode == 0:
        output_size = _file_size(output_file)
        pid = "unknown"
        try:
            pid = Path(pid_file).read_text().strip()
        except Exception:
            pass

        print("Status: RUNNING")
        print(f"Session: {session_id}")
        print(f"PID: {pid}")
        print(f"Output so far: {output_size} bytes")
        print()
        print(f"To view live output: tmux attach -t {session_id}")
        print("To detach: Ctrl-B D")
        sys.exit(1)

    # Not found
    print("Status: NOT FOUND")
    print(f"Session '{session_id}' does not exist and has no completion marker")
    sys.exit(2)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def cleanup(
    older_than: float = 1.0,
    all_sessions: bool = False,
) -> None:
    """Clean up old Small Council tmux sessions and temp files.

    Replicates council-tmux-cleanup.sh behavior.

    Args:
        older_than: Hours threshold (default 1). Ignored when all_sessions is True.
        all_sessions: If True, clean everything (equivalent to --all / hours=0).
    """
    import glob as glob_module

    _require_tmux()

    hours = 0 if all_sessions else older_than
    cutoff = int(time.time()) - int(hours * 3600)
    cleaned = 0

    print(f"=== Cleaning up Small Council sessions older than {hours} hour(s) ===")

    # Kill old tmux sessions
    result = _tmux("list-sessions", "-F", "#{session_name}")
    if result.returncode == 0:
        for session in result.stdout.strip().splitlines():
            if not session.startswith("council-"):
                continue
            # Extract timestamp: council-TIMESTAMP-PID
            parts = session.split("-")
            if len(parts) >= 2:
                try:
                    ts = int(parts[1])
                except (ValueError, IndexError):
                    continue
                if ts < cutoff:
                    print(f"Killing session: {session}")
                    _tmux("kill-session", "-t", session)
                    cleaned += 1

    # Clean up old temp files
    for done_file in glob_module.glob("/tmp/council-*.done"):
        session_name = Path(done_file).stem  # e.g. council-1234567890-12345
        parts = session_name.split("-")
        if len(parts) >= 2:
            try:
                ts = int(parts[1])
            except (ValueError, IndexError):
                continue
            if ts < cutoff:
                print(f"Removing temp files for: {session_name}")
                for suffix in (
                    ".out", ".done", ".pid", ".err",
                    "-wrapper.sh", "-prompt.txt", "-files.txt",
                ):
                    try:
                        os.remove(f"/tmp/{session_name}{suffix}")
                    except OSError:
                        pass
                cleaned += 1

    print()
    print(f"Cleaned up {cleaned} items")
