"""
Fire-and-forget pipeline subprocess spawn utility.

Launches a pipeline step as a detached OS process using the current venv
interpreter. stdout/stderr are discarded (DEVNULL) — all meaningful state
goes to the DB via the pipeline step's own DB writes.

Never await subprocess completion — that would block the FastAPI event loop
and defeat the fire-and-poll pattern. Use Popen and return immediately.

Security: shell=False (default) — args are typed (int job_id, validated str
url/key) and never interpolated into a shell string.
"""

import subprocess
import sys


def spawn_pipeline_step(step: str, job_id: int, extra_args: list[str]) -> None:
    """
    Launch a pipeline step as a detached subprocess and return immediately.

    Args:
        step:       Pipeline subcommand name: "ingest", "parse", or "resolve".
        job_id:     admin_jobs.id — passed as --job-id to the subprocess so it
                    can write status back to the DB.
        extra_args: Additional argv passed after --job-id (e.g. ["--url", url]
                    or ["--spaces-key", key] for ingest; ["--run-id", run_id]
                    for parse and resolve).
    """
    cmd = [sys.executable, "-m", "pipeline", step, "--job-id", str(job_id)] + extra_args
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    # Popen returns immediately; do not block with subprocess.wait or subprocess.communicate
    subprocess.Popen(cmd, **kwargs)
