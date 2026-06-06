import os
import subprocess
import sys

import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture
def run_saturn():
    def _run(cwd, *args):
        env = os.environ.copy()
        src_path = os.path.join(REPO_ROOT, "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "saturn", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            env=env,
        )

    return _run
