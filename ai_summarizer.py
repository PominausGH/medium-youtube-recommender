# ai_summarizer.py
"""Enhanced AI Summarizer with structured output for content analysis."""

import re
import os
from openai import OpenAI
from typing import Dict, Any, List


class AISummarizer:
    """AI-powered content summarizer that provides structured analysis."""

    def __init__(self, api_key: str = None):
        """Initialize the summarizer with OpenAI API key.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        """
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))

    def summarize(self, title: str, content: str, interests: List[str],
                  content_type: str = "article") -> Dict[str, Any]:
        """Analyze content and return structured summary with recommendations.

        Args:
            title: Title of the content
            content: Full text content to analyze
            interests: List of user interests to match against
            content_type: Type of content (article, video, etc.)

        Returns:
            Dict with skill_level, est_read_time, relevance, summary, recommendation
        """
        prompt = f"""Analyze this {content_type} for someone interested in: {', '.join(interests)}

Title: {title}
Content: {content[:1000]}

Provide analysis in this exact format:
Skill level: [Beginner/Intermediate/Advanced]
Est. time: [X min read/watch]
Relevance: [High/Medium/Low] (matches: [which interests])

Summary: [2-3 sentence summary of what this covers]

Verdict: [RECOMMENDED/SKIP] - [one sentence reason]
"""

        try:
            response = self.client.chat.completions.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.5
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            return {
                'skill_level': 'Unknown',
                'est_read_time': None,
                'relevance': 'Unknown',
                'summary': f'Error: {e}',
                'recommendation': 'SKIP',
                'raw_response': str(e)
            }

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse AI response into structured format.

        Args:
            text: Raw response text from the AI model

        Returns:
            Dict with parsed fields
        """
        result = {
            'skill_level': 'Intermediate',
            'est_read_time': None,
            'relevance': 'Medium',
            'summary': '',
            'recommendation': 'SKIP',
            'raw_response': text
        }

        # Parse skill level
        match = re.search(r'Skill level:\s*(Beginner|Intermediate|Advanced)', text, re.I)
        if match:
            result['skill_level'] = match.group(1)

        # Parse time
        match = re.search(r'Est\. time:\s*(\d+)\s*min', text, re.I)
        if match:
            result['est_read_time'] = int(match.group(1))

        # Parse relevance
        match = re.search(r'Relevance:\s*(High|Medium|Low)', text, re.I)
        if match:
            result['relevance'] = match.group(1)

        # Parse summary
        match = re.search(r'Summary:\s*(.+?)(?=Verdict:|$)', text, re.S)
        if match:
            result['summary'] = match.group(1).strip()

        # Parse recommendation
        if 'RECOMMENDED' in text.upper():
            result['recommendation'] = 'RECOMMENDED'
        else:
            result['recommendation'] = 'SKIP'

        return result
