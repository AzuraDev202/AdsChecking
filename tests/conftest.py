"""Run each native desktop scenario in a fresh Tcl/Tk process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def run_desktop_scenario():
    def run(module, scenario):
        root = Path(__file__).resolve().parents[1]
        path = root / 'tests' / module
        code = (
            'import os, runpy, pytest; '
            f'assert os.getpid() != {os.getpid()}; '
            f'scenarios = runpy.run_path({str(path)!r}); '
            'patch = pytest.MonkeyPatch(); '
            f'scenarios[{scenario!r}](patch); '
            'patch.undo()'
        )
        result = subprocess.run([sys.executable, '-c', code], cwd=root,
                                capture_output=True, text=True, timeout=40)
        assert result.returncode == 0, result.stdout + result.stderr
    return run
