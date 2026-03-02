"""Shared Taskwarrior command utilities."""

import logging
import subprocess
import shlex
from typing import Sequence

logger = logging.getLogger(__name__)


def run_taskwarrior_command(command: str | Sequence[str]):
    """Run a task command and return stdout text; return None on task errors."""
    args = shlex.split(command) if isinstance(command, str) else list(command)
    try:
        return subprocess.check_output(args, text=True)
    except subprocess.CalledProcessError as error:
        logger.error("Task command failed: %s", args, exc_info=error)
        return None
