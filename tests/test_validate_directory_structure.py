"""Tests for validate_directory_structure.py — directory completeness checks."""
from conftest import run_validator_with_dir

SCRIPT = 'validate_directory_structure.py'

# Minimal valid structure: skills with 1 md, qa-tests with INDEX.md + journey subdir with 1 md
def _files(extra=None):
    files = {
        'autonoma/skills/login.md': '# Login skill',
        'autonoma/qa-tests/INDEX.md': '---\ntotal_tests: 1\n---\n# Index',
        'autonoma/qa-tests/journey/happy-path.md': '---\ntitle: Happy path\n---\n# Test',
    }
    if extra:
        files.update(extra)
    return files


def test_valid_structure():
    code, out = run_validator_with_dir(SCRIPT, _files(), 'autonoma/qa-tests/INDEX.md')
    assert code == 0
    assert out == 'OK'


def test_valid_with_multiple_subdirs():
    extra = {
        'autonoma/qa-tests/auth/login-test.md': '# auth test',
    }
    code, out = run_validator_with_dir(SCRIPT, _files(extra), 'autonoma/qa-tests/INDEX.md')
    assert code == 0
    assert out == 'OK'


def test_missing_journey_directory():
    files = {
        'autonoma/skills/login.md': '# Login skill',
        'autonoma/qa-tests/INDEX.md': '---\ntotal_tests: 1\n---\n# Index',
        'autonoma/qa-tests/auth/login-test.md': '# auth test',
    }
    code, out = run_validator_with_dir(SCRIPT, files, 'autonoma/qa-tests/INDEX.md')
    assert code == 1
    assert 'missing required "journey" subdirectory' in out


def test_missing_skills_directory():
    files = {
        'autonoma/qa-tests/INDEX.md': '---\ntotal_tests: 1\n---\n# Index',
        'autonoma/qa-tests/journey/happy-path.md': '# Test',
    }
    code, out = run_validator_with_dir(SCRIPT, files, 'autonoma/qa-tests/INDEX.md')
    assert code == 1
    assert 'skills directory not found' in out


def test_skills_directory_empty_no_md():
    files = {
        'autonoma/skills/.gitkeep': '',
        'autonoma/qa-tests/INDEX.md': '---\ntotal_tests: 1\n---\n# Index',
        'autonoma/qa-tests/journey/happy-path.md': '# Test',
    }
    code, out = run_validator_with_dir(SCRIPT, files, 'autonoma/qa-tests/INDEX.md')
    assert code == 1
    assert 'skills directory has no .md files' in out


def test_qa_tests_subdir_empty_no_md():
    files = {
        'autonoma/skills/login.md': '# Login skill',
        'autonoma/qa-tests/INDEX.md': '---\ntotal_tests: 1\n---\n# Index',
        'autonoma/qa-tests/journey/happy-path.md': '# Test',
        'autonoma/qa-tests/empty-folder/.gitkeep': '',
    }
    code, out = run_validator_with_dir(SCRIPT, files, 'autonoma/qa-tests/INDEX.md')
    assert code == 1
    assert 'subdirectory "empty-folder" has no .md files' in out
