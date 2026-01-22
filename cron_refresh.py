#!/usr/bin/env python3
# cron_refresh.py
"""
Automated content refresh script.
Run via cron: 0 6,18 * * * cd /app && python cron_refresh.py >> /var/log/cron.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting content refresh...")

    # Import here to avoid loading everything at module level
    from database import Database
    from sources import ArticleSource, YouTubeSource, RedditSource, StackOverflowSource
    from ai_summarizer import AISummarizer
    from deduplicator import Deduplicator

    db = Database()
    summarizer = AISummarizer()
    deduplicator = Deduplicator()

    # Get active interests
    interests = db.get_interests(active_only=True)
    if not interests:
        logger.info("No active interests. Skipping refresh.")
        return

    topics = [i['topic'] for i in interests]
    logger.info(f"Refreshing content for {len(topics)} interests: {', '.join(topics)}")

    # Initialize sources
    sources = [
        ('articles', ArticleSource()),
        ('youtube', YouTubeSource()),
        ('reddit', RedditSource()),
        ('stackoverflow', StackOverflowSource()),
    ]

    all_content = []

    # Search each interest
    for topic in topics:
        logger.info(f"Searching for: {topic}")

        for source_name, source in sources:
            try:
                results = source.search(topic, limit=5)
                logger.info(f"  {source_name}: {len(results)} results")

                for item in results:
                    # Get AI summary
                    summary_result = summarizer.summarize(
                        title=item.get('title', ''),
                        content=item.get('description', ''),
                        interests=topics,
                        content_type=item.get('source_type', 'article')
                    )

                    item['summary'] = summary_result.get('summary', '')
                    item['recommendation'] = summary_result.get('recommendation', 'SKIP')
                    item['skill_level'] = summary_result.get('skill_level')
                    item['est_read_time'] = summary_result.get('est_read_time')
                    item['relevance_score'] = 1.0 if summary_result.get('relevance') == 'High' else 0.5

                    all_content.append(item)

            except Exception as e:
                logger.error(f"  {source_name} error: {e}")

    # Deduplicate
    logger.info(f"Total content before dedup: {len(all_content)}")
    unique_content = deduplicator.deduplicate(all_content)
    logger.info(f"Total content after dedup: {len(unique_content)}")

    # Save recommended content
    saved_count = 0
    for item in unique_content:
        if item.get('recommendation') == 'RECOMMENDED':
            try:
                db.add_content(
                    title=item.get('title', 'Untitled'),
                    url=item.get('url', ''),
                    source_type=item.get('source_type', 'article'),
                    source_name=item.get('source_name'),
                    summary=item.get('summary'),
                    recommendation=item.get('recommendation'),
                    relevance_score=item.get('relevance_score'),
                    skill_level=item.get('skill_level'),
                    est_read_time=item.get('est_read_time'),
                    thumbnail_url=item.get('thumbnail_url'),
                    raw_date=item.get('raw_date')
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving content: {e}")

    logger.info(f"Saved {saved_count} recommended items to database")
    logger.info("Content refresh complete!")

    db.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        sys.exit(1)
