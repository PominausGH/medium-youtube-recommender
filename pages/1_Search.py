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
api_key = os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY', '')
client = OpenAI(api_key=api_key) if api_key else None

# Page config
st.header('Search')

# Article sources
ARTICLE_SOURCES = {
    'Medium': {'url': 'https://medium.com/feed/tag/{tag}', 'icon': '📝'},
    'Dev.to': {'url': 'https://dev.to/feed/tag/{tag}', 'icon': '👩‍💻'},
    'HackerNoon': {'url': 'https://hackernoon.com/tagged/{tag}/feed', 'icon': '🔧'},
    'Towards Data Science': {'url': 'https://towardsdatascience.com/feed', 'icon': '📊'},
    'freeCodeCamp': {'url': 'https://www.freecodecamp.org/news/rss/', 'icon': '🎓'},
}

AGE_FILTERS = {
    'Any time': None,
    'Past week': 7,
    'Past month': 30,
    'Past year': 365,
}


def parse_youtube_age(time_str):
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
    if not date_str:
        return None
    try:
        pub_date = parsedate_to_datetime(date_str)
        return (datetime.now(pub_date.tzinfo) - pub_date).days
    except Exception:
        return None


def ai_summary(title, text, keywords):
    """Generate AI summary."""
    if not client:
        return "No API key - showing raw content"

    title = title or ''
    text = text or ''
    keywords = [k for k in keywords if k]

    prompt = f"""Title: {title}
Content: {text[:500]}

Interests: {', '.join(keywords) if keywords else 'general tech'}

Give a 1-2 sentence summary. End with RECOMMENDED or SKIP."""

    try:
        response = client.chat.completions.create(
            model='gpt-4',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f'Summary unavailable: {str(e)[:50]}'


def fetch_articles(source_name, rss_url, keywords, max_age_days=None, limit=3):
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
            summary_raw = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()

            results.append({
                'source': source_name,
                'title': title,
                'url': link,
                'date': date_str[:16] if date_str else '',
                'raw_summary': summary_raw[:300],
                'source_type': 'article'
            })
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


def fetch_youtube(query, keywords, max_age_days=None, limit=5):
    try:
        videos = VideosSearch(query, limit=15)
        results = []
        for vid in videos.result().get('result', []):
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

            results.append({
                'source': 'YouTube',
                'title': title,
                'url': link,
                'date': date,
                'thumbnail': thumb_url,
                'raw_summary': desc_text[:300],
                'source_type': 'youtube'
            })
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


def save_item(item, ai_result):
    """Save to reading list."""
    content_id = db.add_content(
        title=item['title'],
        url=item['url'],
        source_type=item['source_type'],
        source_name=item.get('source', 'Unknown'),
        summary=ai_result,
        recommendation='RECOMMENDED' if 'RECOMMENDED' in ai_result else 'SKIP'
    )
    if content_id:
        db.save_item(content_id)
        return True
    return False


# ============ SEARCH INTERFACE ============

# Search terms input
st.markdown("### What do you want to learn?")
search_input = st.text_area(
    "Enter topics (one per line or comma-separated):",
    value="",
    height=100,
    label_visibility="collapsed",
    placeholder="Python\nFastAPI\nMachine Learning"
)

# Parse search terms
search_terms = []
for line in search_input.split('\n'):
    for term in line.split(','):
        term = term.strip()
        if term:
            search_terms.append(term)

if search_terms:
    st.caption(f"Searching for: {', '.join(search_terms)}")

# Sources selection
st.markdown("### Where to search?")

col_articles, col_youtube = st.columns(2)

with col_articles:
    st.markdown("**Articles**")
    selected_sources = []
    for source, info in ARTICLE_SOURCES.items():
        if st.checkbox(f"{info['icon']} {source}", value=(source in ['Medium', 'Dev.to']), key=f"src_{source}"):
            selected_sources.append(source)

with col_youtube:
    st.markdown("**Videos**")
    search_youtube = st.checkbox("🎬 YouTube", value=True)

# Time filter
st.markdown("### How recent?")
age_filter = st.radio(
    "Published within:",
    list(AGE_FILTERS.keys()),
    horizontal=True,
    label_visibility="collapsed"
)
max_age = AGE_FILTERS[age_filter]

st.divider()

# Search button
if st.button('🔍 Search', type='primary', use_container_width=True):
    if not search_terms:
        st.warning("Enter at least one search term")
    else:
        # Initialize results storage
        if 'results' not in st.session_state:
            st.session_state.results = []
        st.session_state.results = []

        progress = st.progress(0, text="Searching...")

        # Fetch articles
        total_steps = len(selected_sources) + (1 if search_youtube else 0)
        step = 0

        for source in selected_sources:
            step += 1
            progress.progress(step / total_steps, text=f"Searching {source}...")

            for term in search_terms[:2]:  # Limit to first 2 terms per source
                tag = term.split()[0].lower()
                rss_url = ARTICLE_SOURCES[source]['url'].format(tag=tag)
                articles = fetch_articles(source, rss_url, search_terms, max_age, limit=2)
                st.session_state.results.extend(articles)

        # Fetch YouTube
        if search_youtube:
            step += 1
            progress.progress(step / total_steps, text="Searching YouTube...")
            query = ' '.join(search_terms[:3])
            videos = fetch_youtube(query, search_terms, max_age, limit=5)
            st.session_state.results.extend(videos)

        progress.empty()

        # Now get AI summaries
        if st.session_state.results:
            st.info(f"Found {len(st.session_state.results)} results. Getting AI summaries...")

            for i, item in enumerate(st.session_state.results):
                item['ai_summary'] = ai_summary(item['title'], item.get('raw_summary', ''), search_terms)

# ============ DISPLAY RESULTS ============

if 'results' in st.session_state and st.session_state.results:
    st.markdown(f"## Results ({len(st.session_state.results)})")

    # Filter tabs
    tab_all, tab_articles, tab_videos = st.tabs(['All', 'Articles', 'Videos'])

    def show_results(filter_type=None):
        results = st.session_state.results
        if filter_type:
            results = [r for r in results if r['source_type'] == filter_type]

        for idx, item in enumerate(results):
            ai_result = item.get('ai_summary', '')
            is_recommended = 'RECOMMENDED' in ai_result.upper()

            with st.container():
                # Header with recommendation badge
                cols = st.columns([1, 6, 2])

                with cols[0]:
                    if is_recommended:
                        st.markdown("🟢")
                    else:
                        st.markdown("🔴")

                with cols[1]:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['source']} • {item.get('date', '')}")

                with cols[2]:
                    # SAVE BUTTON - prominent
                    if st.button("💾 SAVE", key=f"save_{item['source_type']}_{idx}", type="primary"):
                        if save_item(item, ai_result):
                            st.toast("✅ Saved to Reading List!")
                        else:
                            st.toast("Already saved")

                # Show thumbnail for videos
                if item.get('thumbnail'):
                    col_thumb, col_summary = st.columns([1, 3])
                    with col_thumb:
                        st.image(item['thumbnail'], use_container_width=True)
                    with col_summary:
                        st.write(ai_result)
                else:
                    st.write(ai_result)

                # Action links
                link_cols = st.columns(4)
                with link_cols[0]:
                    if item.get('url'):
                        st.link_button("Open", item['url'])
                with link_cols[1]:
                    if item['source_type'] == 'youtube' and item.get('url'):
                        st.link_button("Transcript", f"https://tactiq.io/tools/youtube-transcript?url={item['url']}")

                st.divider()

    with tab_all:
        show_results()

    with tab_articles:
        show_results('article')

    with tab_videos:
        show_results('youtube')

elif 'results' in st.session_state:
    st.info("No results found. Try different search terms or sources.")
