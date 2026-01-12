import streamlit as st
import feedparser
import requests
import os
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'))


# 🧠 AI summarizer
def ai_summary(title, text, keywords):
    prompt = f"""Title: {title}
Content: {text}

Based on these interests: {', '.join(keywords)}, summarize in 2 lines and say 'RECOMMENDED' or 'SKIP' at the end."""

    try:
        response = client.chat.completions.create(model='gpt-4',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.5)
        return response.choices[0].message.content
    except Exception as e:
        return f'❌ AI Error: {e}'

# 🔍 Medium
def check_medium(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link
        summary = BeautifulSoup(entry.summary, 'html.parser').get_text()
        ai_result = ai_summary(title, summary, keywords)
        results.append((title, link, ai_result))
    return results

# 🔍 YouTube
def check_youtube(query, keywords):
    videos = VideosSearch(query, limit=5)
    results = []
    for vid in videos.result()['result']:
        title = vid['title']
        link = vid['link']
        desc_snip = vid.get('descriptionSnippet', '')
        desc_text = ' '.join(d['text'] for d in desc_snip) if desc_snip else ''
        ai_result = ai_summary(title, desc_text, keywords)
        results.append((title, link, ai_result))
    return results

# 🎨 Streamlit UI
st.set_page_config(page_title='AI Article/Video Recommender', layout='wide')
st.title('🔍 AI-Powered Article & Video Recommender')
st.caption('Reads content from Medium & YouTube, summarizes with GPT, and recommends if worth your time.')

keywords_input = st.text_input('Enter your interests (comma separated):', 'Python, AI, machine learning')
keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]

col1, col2 = st.columns(2)

with col1:
    st.subheader('📰 Medium Results')
    medium_feed = 'https://medium.com/feed/tag/python'
    if st.button('Search Medium'):
        results = check_medium(medium_feed, keywords)
        for title, link, ai_result in results:
            st.markdown(f'**{title}**\n\n[Read here]({link})\n\n{ai_result}\n---')

with col2:
    st.subheader('📺 YouTube Results')
    youtube_query = st.text_input('YouTube search query:', 'latest Python tutorials')
    if st.button('Search YouTube'):
        results = check_youtube(youtube_query, keywords)
        for title, link, ai_result in results:
            st.markdown(f'**{title}**\n\n[Watch here]({link})\n\n{ai_result}\n---')
