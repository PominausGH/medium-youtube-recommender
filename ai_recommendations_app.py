import streamlit as st
import feedparser
import os
from bs4 import BeautifulSoup
from youtubesearchpython import VideosSearch
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'))


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
def check_medium(query, keywords):
    tag = query.split()[0].lower() if query else 'python'
    rss_url = f'https://medium.com/feed/tag/{tag}'
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:5]:
            title = entry.title
            link = entry.link
            date = entry.get('published', '')[:16] if entry.get('published') else ''
            summary = BeautifulSoup(entry.summary, 'html.parser').get_text()
            ai_result = ai_summary(title, summary, keywords)
            results.append((title, link, date, ai_result))
        return results
    except Exception as e:
        return [(f'Error fetching Medium', '', '', str(e))]


# YouTube search
def check_youtube(query, keywords):
    try:
        videos = VideosSearch(query, limit=5)
        results = []
        for vid in videos.result()['result']:
            title = vid['title']
            link = vid['link']
            date = vid.get('publishedTime', '')
            desc_snip = vid.get('descriptionSnippet', '')
            desc_text = ' '.join(d['text'] for d in desc_snip) if desc_snip else ''
            ai_result = ai_summary(title, desc_text, keywords)
            results.append((title, link, date, ai_result))
        return results
    except Exception as e:
        return [(f'Error fetching YouTube', '', '', str(e))]


# Streamlit UI
st.set_page_config(page_title='AI Article/Video Recommender', layout='wide')
st.title('AI-Powered Article & Video Recommender')
st.caption('Searches Medium & YouTube, summarizes with GPT, and recommends if worth your time.')

search_query = st.text_input('Search topic:', 'Python machine learning')

if st.button('Search Both', type='primary'):
    keywords = [k.strip() for k in search_query.split() if k.strip()]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Medium Articles')
        with st.spinner('Searching Medium...'):
            results = check_medium(search_query, keywords)
        for title, link, date, ai_result in results:
            st.markdown(f'**{title}**\n\n*{date}* | [Read here]({link})\n\n{ai_result}\n\n---')

    with col2:
        st.subheader('YouTube Videos')
        with st.spinner('Searching YouTube...'):
            results = check_youtube(search_query, keywords)
        for title, link, date, ai_result in results:
            st.markdown(f'**{title}**\n\n*{date}* | [Watch here]({link})\n\n{ai_result}\n\n---')
