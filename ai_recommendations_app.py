import streamlit as st
import feedparser
import os
import re
from datetime import datetime, timedelta
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


def parse_medium_age(date_str):
    """Parse Medium date string to days ago"""
    if not date_str:
        return None
    try:
        pub_date = parsedate_to_datetime(date_str)
        return (datetime.now(pub_date.tzinfo) - pub_date).days
    except:
        return None


# AI summarizer
def ai_summary(title, text, keywords):
    prompt = f"""Title: {title}
Content: {text}

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


# Medium search
def check_medium(query, keywords, max_age_days=None):
    tag = query.split()[0].lower() if query else 'python'
    rss_url = f'https://medium.com/feed/tag/{tag}'
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:10]:  # Check more to filter
            date_str = entry.get('published', '')
            age_days = parse_medium_age(date_str)
            if max_age_days and age_days and age_days > max_age_days:
                continue
            title = entry.title
            link = entry.link
            date = date_str[:16] if date_str else ''
            summary = BeautifulSoup(entry.summary, 'html.parser').get_text()
            ai_result = ai_summary(title, summary, keywords)
            results.append((title, link, date, ai_result))
            if len(results) >= 5:
                break
        return results
    except Exception as e:
        return [(f'Error fetching Medium', '', '', str(e))]


# YouTube search
def check_youtube(query, keywords, max_age_days=None):
    try:
        videos = VideosSearch(query, limit=15)  # Get more to filter
        results = []
        for vid in videos.result()['result']:
            date = vid.get('publishedTime', '')
            age_days = parse_youtube_age(date)
            if max_age_days and age_days and age_days > max_age_days:
                continue
            title = vid['title']
            link = vid['link']
            thumbnails = vid.get('thumbnails', [])
            thumb_url = thumbnails[0]['url'] if thumbnails else ''
            desc_snip = vid.get('descriptionSnippet', '')
            desc_text = ' '.join(d['text'] for d in desc_snip) if desc_snip else ''
            ai_result = ai_summary(title, desc_text, keywords)
            results.append((title, link, date, thumb_url, ai_result))
            if len(results) >= 5:
                break
        return results
    except Exception as e:
        return [(f'Error fetching YouTube', '', '', '', str(e))]


# Streamlit UI
st.set_page_config(page_title='AI Article/Video Recommender', layout='wide')
st.title('AI-Powered Article & Video Recommender')
st.caption('Searches Medium & YouTube, summarizes with GPT, and recommends if worth your time.')

col_search, col_filter = st.columns([3, 1])
with col_search:
    search_query = st.text_input('Search topic:', 'Python machine learning')
with col_filter:
    age_filter = st.selectbox('Published:', list(AGE_FILTERS.keys()))

max_age = AGE_FILTERS[age_filter]

if st.button('Search Both', type='primary'):
    keywords = [k.strip() for k in search_query.split() if k.strip()]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Medium Articles')
        with st.spinner('Searching Medium...'):
            results = check_medium(search_query, keywords, max_age)
        if not results:
            st.info('No articles found in this time range')
        for title, link, date, ai_result in results:
            st.markdown(f'**{title}**\n\n*{date}* | [Read here]({link})\n\n{ai_result}\n\n---')

    with col2:
        st.subheader('YouTube Videos')
        with st.spinner('Searching YouTube...'):
            results = check_youtube(search_query, keywords, max_age)
        if not results:
            st.info('No videos found in this time range')
        for title, link, date, thumb_url, ai_result in results:
            if thumb_url:
                st.image(thumb_url, width=280)
            st.markdown(f'**{title}**\n\n*{date}* | [Watch here]({link})\n\n{ai_result}\n\n---')
