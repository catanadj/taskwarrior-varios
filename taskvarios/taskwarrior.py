"""Shared Taskwarrior command utilities."""

import subprocess


def run_taskwarrior_command(command: str):
    """Run a shell command and return stdout text; return None on task errors."""
    try:
        return subprocess.check_output(command, shell=True, text=True)
    except subprocess.CalledProcessError as error:
        print(f"An error occurred: {error}")
        return None
