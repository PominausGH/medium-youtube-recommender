# interest_suggester.py
"""LLM-powered interest suggester based on project scans."""

import os
import re
from openai import OpenAI
from typing import Dict, List, Any


class InterestSuggester:
    """Suggests learning topics and problem-solving content based on project analysis."""

    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key."""
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))

    def suggest(self, scan_result: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """Generate content suggestions based on project scan results.

        Args:
            scan_result: Dictionary with 'technologies' and 'todos' keys from ProjectScanner

        Returns:
            Dictionary with 'learning' and 'problem_solving' keys containing topic suggestions
        """
        technologies = scan_result.get('technologies', [])
        todos = scan_result.get('todos', [])

        if not technologies and not todos:
            return {'learning': [], 'problem_solving': []}

        prompt = f"""Based on this project analysis, suggest content topics:

Technologies detected: {', '.join(technologies) if technologies else 'None'}

TODOs/Problems found:
{self._format_todos(todos)}

Suggest topics in two categories:

LEARNING:
- Topics to learn more about the technologies used (3-5 suggestions)

PROBLEM_SOLVING:
- Topics that would help solve the TODOs (1-3 suggestions based on TODOs)

Format each as a bullet point with a brief reason in parentheses."""

        try:
            response = self.client.chat.completions.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7
            )
            return self._parse_suggestions(response.choices[0].message.content)
        except Exception as e:
            return {'learning': [], 'problem_solving': [], 'error': str(e)}

    def _format_todos(self, todos: List[Dict[str, str]]) -> str:
        """Format TODOs for inclusion in the prompt.

        Args:
            todos: List of TODO dictionaries with 'file' and 'text' keys

        Returns:
            Formatted string of TODOs or 'None' if empty
        """
        if not todos:
            return "None"
        return '\n'.join(f"- {t['text']} ({t['file']})" for t in todos[:10])

    def _parse_suggestions(self, text: str) -> Dict[str, List[Dict[str, str]]]:
        """Parse LLM response into structured suggestions.

        Args:
            text: Raw text response from the LLM

        Returns:
            Dictionary with 'learning' and 'problem_solving' lists
        """
        result = {'learning': [], 'problem_solving': []}

        current_section = None
        for line in text.split('\n'):
            line = line.strip()

            # Check for items first (before section headers)
            if line.startswith('-') and current_section:
                # Parse "- Topic (reason)" format
                match = re.match(r'-\s*(.+?)(?:\s*\((.+)\))?$', line)
                if match:
                    topic = match.group(1).strip()
                    reason = match.group(2).strip() if match.group(2) else ''
                    result[current_section].append({
                        'topic': topic,
                        'reason': reason
                    })
            # Check for section headers (lines not starting with -)
            elif 'LEARNING' in line.upper():
                current_section = 'learning'
            elif 'PROBLEM' in line.upper() or 'SOLVING' in line.upper():
                current_section = 'problem_solving'

        return result
