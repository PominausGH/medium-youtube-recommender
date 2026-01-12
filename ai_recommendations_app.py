import streamlit as st
import feedparser
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'))

# Age filter options (in days)
AGE_FILTERS = {
    'Any time': None,
    'Past week': 7,
    'Past month': 30,
    'Past 3 months': 90,
    'Past year': 365,
}

# Article sources with RSS feed templates ({tag} is replaced with search term)
ARTICLE_SOURCES = {
    'Medium': 'https://medium.com/feed/tag/{tag}',
    'Dev.to': 'https://dev.to/feed/tag/{tag}',
    'HackerNoon': 'https://hackernoon.com/tagged/{tag}/feed',
    'Towards Data Science': 'https://towardsdatascience.com/feed',
    'freeCodeCamp': 'https://www.freecodecamp.org/news/rss/',
}


def parse_youtube_age(time_str):
    """Parse YouTube relative time like '10 months ago' to days"""
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
    """Parse article date string to days ago"""
    if not date_str:
        return None
    try:
        pub_date = parsedate_to_datetime(date_str)
        return (datetime.now(pub_date.tzinfo) - pub_date).days
    except:
        return None


# AI summarizer
def ai_summary(title, text, keywords):
    title = title or ''
    text = text or ''
    keywords = [k for k in keywords if k]  # Filter out None/empty
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
    """Fetch articles from an RSS feed"""
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
            results.append((source_name, title, link, date, ai_result))
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        return []


def check_articles(query, keywords, sources, max_age_days=None):
    """Search multiple article sources"""
    tag = query.split()[0].lower() if query else 'python'
    all_results = []

    for source_name in sources:
        if source_name in ARTICLE_SOURCES:
            rss_url = ARTICLE_SOURCES[source_name].format(tag=tag)
            results = fetch_articles(source_name, rss_url, keywords, max_age_days, limit=3)
            all_results.extend(results)

    return all_results


def check_youtube(query, keywords, max_age_days=None):
    """Search YouTube videos"""
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
            results.append((title, link, date, thumb_url, ai_result))
            if len(results) >= 5:
                break
        return results
    except Exception as e:
        return [('Error fetching YouTube', '', '', '', str(e))]


# Streamlit UI
st.set_page_config(page_title='AI Article/Video Recommender', layout='wide')
st.title('AI-Powered Article & Video Recommender')
st.caption('Searches multiple platforms, summarizes with GPT, and recommends if worth your time.')

# Search controls
col_search, col_filter = st.columns([3, 1])
with col_search:
    search_query = st.text_input('Search topic:', 'Python machine learning')
with col_filter:
    age_filter = st.selectbox('Published:', list(AGE_FILTERS.keys()))

# Source selection
selected_sources = st.multiselect(
    'Article sources:',
    list(ARTICLE_SOURCES.keys()),
    default=['Medium', 'Dev.to']
)

max_age = AGE_FILTERS[age_filter]

if st.button('Search All', type='primary'):
    keywords = [k.strip() for k in search_query.split() if k.strip()]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Articles')
        if selected_sources:
            with st.spinner(f'Searching {", ".join(selected_sources)}...'):
                results = check_articles(search_query, keywords, selected_sources, max_age)
            if not results:
                st.info('No articles found in this time range')
            for source, title, link, date, ai_result in results:
                st.markdown(f'**[{source}]** {title}\n\n*{date}* | [Read here]({link})\n\n{ai_result}\n\n---')
        else:
            st.info('Select at least one article source')

    with col2:
        st.subheader('YouTube Videos')
        with st.spinner('Searching YouTube...'):
            results = check_youtube(search_query, keywords, max_age)
        if not results:
            st.info('No videos found in this time range')
        for title, link, date, thumb_url, ai_result in results:
            if thumb_url:
                st.image(thumb_url, width=280)
            transcript_link = f'https://tactiq.io/tools/youtube-transcript?url={link}' if link else ''
            st.markdown(f'**{title}**\n\n*{date or ""}* | [Watch]({link}) | [Transcript]({transcript_link})\n\n{ai_result}\n\n---')
