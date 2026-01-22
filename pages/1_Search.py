# pages/1_Search.py
"""Search page - manual search across all content sources."""

import streamlit as st
import feedparser
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch
from openai import OpenAI

# Initialize database
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Get OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY', ''))

st.header('Search')

# Age filter options (in days)
AGE_FILTERS = {
    'Any time': None,
    'Past week': 7,
    'Past month': 30,
    'Past 3 months': 90,
    'Past year': 365,
}

# Article sources with RSS feed templates
ARTICLE_SOURCES = {
    'Medium': 'https://medium.com/feed/tag/{tag}',
    'Dev.to': 'https://dev.to/feed/tag/{tag}',
    'HackerNoon': 'https://hackernoon.com/tagged/{tag}/feed',
    'Towards Data Science': 'https://towardsdatascience.com/feed',
    'freeCodeCamp': 'https://www.freecodecamp.org/news/rss/',
}


def parse_youtube_age(time_str):
    """Parse YouTube relative time like '10 months ago' to days."""
    if not time_str:
        return None
    match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago', time_str.lower())
    if not match:
        return None
    num = int(match.group(1))
    unit = match.group(2)
    multipliers = {'second': 1/86400, 'minute': 1/1440, 'hour': 1/24, 'day': 1, 'week': 7, 'month': 30, 'year': 365}
    return num * multipliers.get(unit, 1)


def parse_article_age(date_str):
    """Parse article date string to days ago."""
    if not date_str:
        return None
    try:
        pub_date = parsedate_to_datetime(date_str)
        return (datetime.now(pub_date.tzinfo) - pub_date).days
    except Exception:
        return None


def ai_summary(title, text, keywords):
    """Generate AI summary and recommendation for content."""
    title = title or ''
    text = text or ''
    keywords = [k for k in keywords if k]
    prompt = f"""Title: {title}
Content: {text[:500]}

Based on these interests: {', '.join(keywords)}, summarize in 2 lines and say 'RECOMMENDED' or 'SKIP' at the end."""

    try:
        response = client.chat.completions.create(
            model='gpt-4',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f'Error: {e}'


def fetch_articles(source_name, rss_url, keywords, max_age_days=None, limit=3):
    """Fetch articles from an RSS feed."""
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:10]:
            date_str = entry.get('published') or entry.get('updated') or ''
            age_days = parse_article_age(date_str)
            if max_age_days and age_days and age_days > max_age_days:
                continue
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            date = date_str[:16] if date_str else ''
            summary = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
            ai_result = ai_summary(title, summary, keywords)
            results.append({
                'source': source_name,
                'title': title,
                'url': link,
                'date': date,
                'summary': summary[:300],
                'ai_summary': ai_result,
                'source_type': 'article'
            })
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


def check_articles(query, keywords, sources, max_age_days=None):
    """Search multiple article sources."""
    tag = query.split()[0].lower() if query else 'python'
    all_results = []
    for source_name in sources:
        if source_name in ARTICLE_SOURCES:
            rss_url = ARTICLE_SOURCES[source_name].format(tag=tag)
            results = fetch_articles(source_name, rss_url, keywords, max_age_days, limit=3)
            all_results.extend(results)
    return all_results


def check_youtube(query, keywords, max_age_days=None):
    """Search YouTube videos."""
    try:
        videos = VideosSearch(query, limit=15)
        results = []
        for vid in videos.result()['result']:
            date = vid.get('publishedTime') or ''
            age_days = parse_youtube_age(date)
            if max_age_days and age_days and age_days > max_age_days:
                continue
            title = vid.get('title') or 'No title'
            link = vid.get('link') or ''
            thumbnails = vid.get('thumbnails') or []
            thumb_url = thumbnails[0].get('url', '') if thumbnails else ''
            desc_snip = vid.get('descriptionSnippet') or []
            desc_text = ' '.join(str(d.get('text', '')) for d in desc_snip) if desc_snip else ''
            ai_result = ai_summary(title, desc_text, keywords)
            results.append({
                'title': title,
                'url': link,
                'date': date,
                'thumbnail': thumb_url,
                'summary': desc_text[:300],
                'ai_summary': ai_result,
                'source_type': 'youtube',
                'source': 'YouTube'
            })
            if len(results) >= 5:
                break
        return results
    except Exception as e:
        return []


def save_to_reading_list(item):
    """Save a search result to the reading list."""
    # First add to content table
    content_id = db.add_content(
        title=item['title'],
        url=item['url'],
        source_type=item['source_type'],
        source_name=item.get('source', 'Unknown'),
        summary=item.get('ai_summary', ''),
        recommendation='RECOMMENDED'
    )
    if content_id:
        # Then save to reading list
        db.save_item(content_id)
        return True
    return False


def display_article_card(item, idx):
    """Display an article result as a card."""
    is_recommended = 'RECOMMENDED' in item.get('ai_summary', '')

    with st.container():
        # Header row
        col_badge, col_source = st.columns([1, 4])
        with col_badge:
            if is_recommended:
                st.success("RECOMMENDED", icon="\u2713")
            else:
                st.warning("SKIP", icon="\u2717")
        with col_source:
            st.caption(f"{item['source']} | {item.get('date', '')}")

        # Title
        st.markdown(f"### {item['title']}")

        # AI Summary
        if item.get('ai_summary'):
            st.info(item['ai_summary'])

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Save", key=f"save_art_{idx}", type="primary"):
                if save_to_reading_list(item):
                    st.toast("Saved to Reading List!", icon="\u2705")
                else:
                    st.toast("Already saved", icon="\u2139")
        with col2:
            st.link_button("Read", item['url'])

        st.divider()


def display_video_card(item, idx):
    """Display a video result as a card."""
    is_recommended = 'RECOMMENDED' in item.get('ai_summary', '')

    with st.container():
        col_thumb, col_content = st.columns([1, 2])

        with col_thumb:
            if item.get('thumbnail'):
                st.image(item['thumbnail'], use_container_width=True)

        with col_content:
            # Badge and date
            if is_recommended:
                st.success("RECOMMENDED", icon="\u2713")
            else:
                st.warning("SKIP", icon="\u2717")

            st.caption(item.get('date', ''))

            # Title
            st.markdown(f"**{item['title']}**")

            # AI Summary
            if item.get('ai_summary'):
                st.info(item['ai_summary'])

            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Save", key=f"save_vid_{idx}", type="primary"):
                    if save_to_reading_list(item):
                        st.toast("Saved to Reading List!", icon="\u2705")
                    else:
                        st.toast("Already saved", icon="\u2139")
            with col2:
                if item.get('url'):
                    st.link_button("Watch", item['url'])
            with col3:
                if item.get('url'):
                    transcript_link = f"https://tactiq.io/tools/youtube-transcript?url={item['url']}"
                    st.link_button("Transcript", transcript_link)

        st.divider()


# Search controls
with st.container():
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input('Search topic:', 'Python machine learning', label_visibility="collapsed", placeholder="Enter search topic...")
    with col_filter:
        age_filter = st.selectbox('Published:', list(AGE_FILTERS.keys()), label_visibility="collapsed")

# Source selection
selected_sources = st.multiselect(
    'Article sources:',
    list(ARTICLE_SOURCES.keys()),
    default=['Medium', 'Dev.to'],
    label_visibility="collapsed"
)

max_age = AGE_FILTERS[age_filter]

if st.button('Search', type='primary', use_container_width=True):
    keywords = [k.strip() for k in search_query.split() if k.strip()]

    # Store results in session state
    st.session_state.search_results = {'articles': [], 'videos': []}

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Articles')
        if selected_sources:
            with st.spinner(f'Searching {", ".join(selected_sources)}...'):
                articles = check_articles(search_query, keywords, selected_sources, max_age)
                st.session_state.search_results['articles'] = articles

            if not articles:
                st.info('No articles found in this time range')
            else:
                for idx, item in enumerate(articles):
                    display_article_card(item, idx)
        else:
            st.info('Select at least one article source above')

    with col2:
        st.subheader('YouTube Videos')
        with st.spinner('Searching YouTube...'):
            videos = check_youtube(search_query, keywords, max_age)
            st.session_state.search_results['videos'] = videos

        if not videos:
            st.info('No videos found in this time range')
        else:
            for idx, item in enumerate(videos):
                display_video_card(item, idx)

# Display previous results if available (for when save button is clicked)
elif 'search_results' in st.session_state and (st.session_state.search_results.get('articles') or st.session_state.search_results.get('videos')):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Articles')
        articles = st.session_state.search_results.get('articles', [])
        if articles:
            for idx, item in enumerate(articles):
                display_article_card(item, idx)

    with col2:
        st.subheader('YouTube Videos')
        videos = st.session_state.search_results.get('videos', [])
        if videos:
            for idx, item in enumerate(videos):
                display_video_card(item, idx)
