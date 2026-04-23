"""Shared helpers for validator tests."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

VALIDATORS_DIR = os.path.join(os.path.dirname(__file__), '..', 'hooks', 'validators')
sys.path.insert(0, str(Path(VALIDATORS_DIR).resolve()))
REPO_ROOT = Path(__file__).resolve().parent.parent


def _ensure_test_requirements() -> None:
    try:
        import pydantic  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-r', str(REPO_ROOT / 'requirements.txt')],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


_ensure_test_requirements()


def run_validator(script_name: str, content: str, filename: str = 'test.md') -> tuple[int, str]:
    """Write content to a temp file, run the validator, return (exit_code, output)."""
    script = os.path.join(VALIDATORS_DIR, script_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        result = subprocess.run(
            [sys.executable, script, filepath],
            capture_output=True, text=True,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output


def run_validator_with_dir(script_name: str, files: dict[str, str], target: str) -> tuple[int, str]:
    """Write multiple files into a temp dir tree, run validator on target, return (exit_code, output).

    files: mapping of relative paths to content (e.g. {'autonoma/qa-tests/INDEX.md': '...'})
    target: relative path within the temp dir to validate
    """
    script = os.path.join(VALIDATORS_DIR, script_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        for relpath, content in files.items():
            fullpath = os.path.join(tmpdir, relpath)
            os.makedirs(os.path.dirname(fullpath), exist_ok=True)
            with open(fullpath, 'w') as f:
                f.write(content)
        filepath = os.path.join(tmpdir, target)
        result = subprocess.run(
            [sys.executable, script, filepath],
            capture_output=True, text=True,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
