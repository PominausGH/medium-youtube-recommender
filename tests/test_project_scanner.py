# tests/test_project_scanner.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from project_scanner import ProjectScanner


def test_detect_python_project():
    """Test detection of Python project with requirements.txt."""
    scanner = ProjectScanner()
    files = {
        'requirements.txt': 'fastapi==0.100.0\nsqlalchemy==2.0.0',
        'main.py': '# TODO: add authentication\nimport fastapi',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'fastapi' in [t.lower() for t in result['technologies']]
    assert len(result['todos']) >= 1


def test_detect_technologies_from_package_json():
    """Test detection of JavaScript project with package.json."""
    scanner = ProjectScanner()
    files = {
        'package.json': '{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    techs_lower = [t.lower() for t in result['technologies']]
    assert 'react' in techs_lower or 'javascript' in techs_lower


def test_detect_rust_project():
    """Test detection of Rust project with Cargo.toml."""
    scanner = ProjectScanner()
    files = {
        'Cargo.toml': '[package]\nname = "myproject"\nversion = "0.1.0"',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'Rust' in result['technologies']


def test_detect_go_project():
    """Test detection of Go project with go.mod."""
    scanner = ProjectScanner()
    files = {
        'go.mod': 'module example.com/myproject\n\ngo 1.21',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'Go' in result['technologies']


def test_detect_todos_in_python_file():
    """Test extraction of TODO comments from Python files."""
    scanner = ProjectScanner()
    files = {
        'app.py': '''# TODO: implement user auth
def login():
    pass
# FIXME: handle edge cases
# HACK: temporary workaround
''',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert len(result['todos']) == 3
    todo_texts = [t['text'] for t in result['todos']]
    assert 'implement user auth' in todo_texts
    assert 'handle edge cases' in todo_texts
    assert 'temporary workaround' in todo_texts


def test_detect_todos_in_javascript_file():
    """Test extraction of TODO comments from JavaScript files."""
    scanner = ProjectScanner()
    files = {
        'app.js': '''// TODO: add error handling
function doSomething() {
    // FIXME: memory leak here
}
''',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert len(result['todos']) == 2


def test_todos_limited_to_20():
    """Test that TODOs are limited to 20 entries."""
    scanner = ProjectScanner()
    # Create 30 TODOs
    todos = '\n'.join([f'# TODO: task {i}' for i in range(30)])
    files = {
        'big_file.py': todos,
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert len(result['todos']) <= 20


def test_scan_returns_structure():
    """Test that scan returns expected structure."""
    scanner = ProjectScanner()
    files = {}

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'technologies' in result
    assert 'todos' in result
    assert isinstance(result['technologies'], list)
    assert isinstance(result['todos'], list)


def test_detect_pyproject_toml():
    """Test detection of Python project with pyproject.toml."""
    scanner = ProjectScanner()
    files = {
        'pyproject.toml': '[tool.poetry]\nname = "myproject"',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'Python' in result['technologies']


def test_scan_github_clone_failure():
    """Test handling of failed GitHub clone."""
    scanner = ProjectScanner()

    with patch('subprocess.run', side_effect=Exception('Clone failed')):
        result = scanner.scan_github('https://github.com/invalid/repo')

    assert 'error' in result


def test_cleanup_removes_temp_dir():
    """Test that cleanup removes temporary directory."""
    scanner = ProjectScanner()
    scanner.temp_dir = '/tmp/test_cleanup_dir'

    with patch('os.path.exists', return_value=True):
        with patch('shutil.rmtree') as mock_rmtree:
            scanner.cleanup()
            mock_rmtree.assert_called_once()


def test_read_file_handles_errors():
    """Test that _read_file handles errors gracefully."""
    scanner = ProjectScanner()
    result = scanner._read_file('/nonexistent/path/file.txt')
    assert result == ''


def test_multiple_technologies_detected():
    """Test detection of multiple technologies in same project."""
    scanner = ProjectScanner()
    files = {
        'requirements.txt': 'flask==2.0.0\npytest==7.0.0',
        'package.json': '{"dependencies": {"typescript": "^5.0.0"}}',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    techs_lower = [t.lower() for t in result['technologies']]
    assert 'python' in techs_lower
    assert 'javascript' in techs_lower
