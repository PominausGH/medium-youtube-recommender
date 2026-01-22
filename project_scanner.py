# project_scanner.py
"""Project scanner for detecting technologies and TODOs in codebases."""

import os
import re
import json
import tempfile
import subprocess
from typing import Dict, List, Any
from pathlib import Path


class ProjectScanner:
    """Scans local or GitHub repositories for technologies and TODOs."""

    TODO_PATTERNS = [
        r'#\s*TODO[:\s](.+)',
        r'#\s*FIXME[:\s](.+)',
        r'#\s*HACK[:\s](.+)',
        r'//\s*TODO[:\s](.+)',
        r'//\s*FIXME[:\s](.+)',
    ]

    # Known packages/dependencies to detect
    PYTHON_PACKAGES = ['fastapi', 'django', 'flask', 'sqlalchemy', 'pytest', 'numpy', 'pandas']
    JS_PACKAGES = ['react', 'vue', 'angular', 'express', 'next', 'typescript', 'svelte']

    def __init__(self):
        self.temp_dir = None

    def _read_file(self, filepath: str) -> str:
        """Read file contents, returning empty string on error."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ''

    def _list_files(self, directory: str) -> List[str]:
        """List all files in directory recursively."""
        files = []
        try:
            for root, _, filenames in os.walk(directory):
                # Skip common directories to ignore
                if any(skip in root for skip in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']):
                    continue
                for filename in filenames:
                    files.append(os.path.join(root, filename))
        except Exception:
            pass
        return files

    def scan_github(self, repo_url: str) -> Dict[str, Any]:
        """Clone a GitHub repo and scan it."""
        self.temp_dir = tempfile.mkdtemp()
        try:
            subprocess.run(
                ['git', 'clone', '--depth', '1', repo_url, self.temp_dir],
                check=True, capture_output=True
            )
            return self.scan_local(self.temp_dir)
        except subprocess.CalledProcessError:
            return {'technologies': [], 'todos': [], 'error': 'Failed to clone repository'}
        except Exception as e:
            return {'technologies': [], 'todos': [], 'error': str(e)}

    def scan_local(self, directory: str) -> Dict[str, Any]:
        """Scan a local directory for technologies and TODOs."""
        technologies = set()
        todos = []

        files = self._list_files(directory)

        for f in files:
            # Check for Python project
            if f.endswith('requirements.txt'):
                content = self._read_file(f)
                technologies.add('Python')
                self._detect_python_packages(content, technologies)

            if f.endswith('pyproject.toml'):
                technologies.add('Python')

            # Check for JavaScript/Node project
            if f.endswith('package.json'):
                content = self._read_file(f)
                technologies.add('JavaScript')
                self._detect_js_packages(content, technologies)

            # Check for Rust project
            if f.endswith('Cargo.toml'):
                technologies.add('Rust')

            # Check for Go project
            if f.endswith('go.mod'):
                technologies.add('Go')

        # Find TODOs in source files
        todos = self._extract_todos(files)

        return {
            'technologies': list(technologies),
            'todos': todos[:20],  # Limit to 20 TODOs
        }

    def _detect_python_packages(self, content: str, technologies: set) -> None:
        """Detect Python packages from requirements.txt content."""
        for line in content.split('\n'):
            line = line.strip().lower()
            # Handle various requirement formats: pkg==1.0, pkg>=1.0, pkg
            for separator in ['==', '>=', '<=', '>', '<', '~=', '[']:
                if separator in line:
                    pkg = line.split(separator)[0].strip()
                    break
            else:
                pkg = line

            if pkg in self.PYTHON_PACKAGES:
                technologies.add(pkg.capitalize())

    def _detect_js_packages(self, content: str, technologies: set) -> None:
        """Detect JavaScript packages from package.json content."""
        try:
            pkg = json.loads(content)
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            for dep in deps:
                dep_lower = dep.lower()
                if dep_lower in self.JS_PACKAGES:
                    technologies.add(dep.capitalize())
        except json.JSONDecodeError:
            pass

    def _extract_todos(self, files: List[str]) -> List[Dict[str, str]]:
        """Extract TODO comments from source files."""
        todos = []
        source_extensions = ['.py', '.js', '.ts', '.rs', '.go', '.java', '.tsx', '.jsx']

        for f in files:
            if any(f.endswith(ext) for ext in source_extensions):
                content = self._read_file(f)
                for pattern in self.TODO_PATTERNS:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        todos.append({
                            'file': os.path.basename(f),
                            'text': match.strip()
                        })

        return todos

    def cleanup(self):
        """Clean up temporary directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
