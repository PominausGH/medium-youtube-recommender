# app.py
"""Main entry point for the AI Content Curator multi-page Streamlit app."""

import streamlit as st

st.set_page_config(
    page_title='AI Content Curator',
    page_icon='📚',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.title('AI Content Curator')
st.caption('Automated content curation based on your interests and projects.')

st.markdown('''
## Welcome!

Use the sidebar to navigate:

- **Search** - Manual search across all sources
- **My Feed** - AI-curated content based on your interests
- **Interests** - Manage topics and scan projects
- **Reading List** - Saved content and Obsidian sync
- **Settings** - Configure the app
''')

# Initialize database connection in session state
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()
