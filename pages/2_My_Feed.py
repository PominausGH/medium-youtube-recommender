# pages/2_My_Feed.py
"""My Feed page - personalized content recommendations based on interests."""

import streamlit as st
from datetime import datetime

st.header('My Feed')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Header with refresh button
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    interests = db.get_interests(active_only=True)
    if interests:
        topics = [i['topic'] for i in interests[:5]]
        st.caption(f"Based on: {', '.join(topics)}")
    else:
        st.caption("No interests configured yet")

with col2:
    if st.button('Refresh Now'):
        st.info('Refresh functionality coming soon')

with col3:
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M')}")

# Filter tabs
tab_all, tab_articles, tab_videos, tab_reddit, tab_so = st.tabs([
    'All', 'Articles', 'Videos', 'Reddit', 'Stack Overflow'
])


# Get recommended content
def display_content(source_type=None):
    """Display content items with action buttons."""
    content = db.get_recommended_content(source_type=source_type, limit=20)

    if not content:
        st.info('No content yet. Add interests and refresh to get recommendations.')
        return

    for item in content:
        with st.container():
            # Relevance badge
            relevance = item.get('relevance_score', 0)
            if relevance and relevance > 0.7:
                st.markdown('**HIGH MATCH**')

            # Title and source
            st.markdown(f"**{item['title']}** - {item.get('source_name', 'Unknown')}")

            # Metadata
            meta_parts = []
            if item.get('est_read_time'):
                meta_parts.append(f"{item['est_read_time']} min read")
            if item.get('skill_level'):
                meta_parts.append(item['skill_level'])
            if meta_parts:
                st.caption(' | '.join(meta_parts))

            # Summary
            if item.get('summary'):
                summary_text = item['summary']
                if len(summary_text) > 200:
                    st.write(summary_text[:200] + '...')
                else:
                    st.write(summary_text)

            # Action buttons
            col_save, col_skip, col_open = st.columns(3)
            with col_save:
                if st.button('Save', key=f"save_{item['id']}"):
                    db.save_item(item['id'])
                    db.record_action(item['id'], 'saved')
                    st.success('Saved!')
            with col_skip:
                if st.button('Skip', key=f"skip_{item['id']}"):
                    db.record_action(item['id'], 'skipped')
                    st.rerun()
            with col_open:
                st.link_button('Open', item['url'])

            st.divider()


with tab_all:
    display_content()

with tab_articles:
    display_content('article')

with tab_videos:
    display_content('youtube')

with tab_reddit:
    display_content('reddit')

with tab_so:
    display_content('stackoverflow')
