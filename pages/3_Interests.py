# pages/3_Interests.py
"""Interests page - manage topics and scan projects for suggestions."""

import streamlit as st
from project_scanner import ProjectScanner
from interest_suggester import InterestSuggester
import os

st.header('Interests')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Manual interest input
st.subheader('Add Interest')
col_input, col_add = st.columns([3, 1])
with col_input:
    new_topic = st.text_input('Topic', placeholder='e.g., FastAPI, machine learning')
with col_add:
    if st.button('Add', type='primary'):
        if new_topic.strip():
            db.add_interest(new_topic.strip(), source='manual')
            st.success(f'Added: {new_topic}')
            st.rerun()

st.divider()

# Project scanning
st.subheader('Scan Project')
st.caption('Scan a GitHub repo or local folder to get interest suggestions.')

scan_tab_github, scan_tab_local = st.tabs(['GitHub URL', 'Local Folder'])

with scan_tab_github:
    github_url = st.text_input('GitHub Repository URL', placeholder='https://github.com/user/repo')
    if st.button('Scan GitHub'):
        if github_url:
            with st.spinner('Cloning and scanning...'):
                scanner = ProjectScanner()
                try:
                    scan_result = scanner.scan_github(github_url)
                    st.session_state.scan_result = scan_result
                    st.session_state.scan_source = github_url

                    # Get LLM suggestions
                    if os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'):
                        suggester = InterestSuggester()
                        suggestions = suggester.suggest(scan_result)
                        st.session_state.suggestions = suggestions
                finally:
                    scanner.cleanup()

with scan_tab_local:
    local_path = st.text_input('Folder Path', placeholder='/path/to/project')
    if st.button('Scan Local'):
        if local_path and os.path.isdir(local_path):
            with st.spinner('Scanning...'):
                scanner = ProjectScanner()
                scan_result = scanner.scan_local(local_path)
                st.session_state.scan_result = scan_result
                st.session_state.scan_source = local_path

                if os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'):
                    suggester = InterestSuggester()
                    suggestions = suggester.suggest(scan_result)
                    st.session_state.suggestions = suggestions

# Display scan results
if 'scan_result' in st.session_state:
    result = st.session_state.scan_result
    st.success(f"Scanned: {st.session_state.get('scan_source', 'Unknown')}")

    col_tech, col_todos = st.columns(2)
    with col_tech:
        st.markdown('**Technologies detected:**')
        for tech in result.get('technologies', []):
            st.markdown(f"- {tech}")

    with col_todos:
        st.markdown('**TODOs found:**')
        for todo in result.get('todos', [])[:5]:
            st.markdown(f"- {todo['text'][:50]}...")

# Display suggestions
if 'suggestions' in st.session_state:
    suggestions = st.session_state.suggestions

    st.subheader('Suggested Interests')

    if suggestions.get('learning'):
        st.markdown('**Learning Topics:**')
        for item in suggestions['learning']:
            col_topic, col_action = st.columns([3, 1])
            with col_topic:
                st.markdown(f"- {item['topic']}")
                if item.get('reason'):
                    st.caption(item['reason'])
            with col_action:
                if st.button('Add', key=f"add_learn_{item['topic']}"):
                    db.add_interest(item['topic'], source='llm')
                    st.success(f"Added: {item['topic']}")

    if suggestions.get('problem_solving'):
        st.markdown('**Problem-Solving Topics:**')
        for item in suggestions['problem_solving']:
            col_topic, col_action = st.columns([3, 1])
            with col_topic:
                st.markdown(f"- {item['topic']}")
                if item.get('reason'):
                    st.caption(item['reason'])
            with col_action:
                if st.button('Add', key=f"add_prob_{item['topic']}"):
                    db.add_interest(item['topic'], source='llm')
                    st.success(f"Added: {item['topic']}")

st.divider()

# Current interests
st.subheader('Your Interests')
interests = db.get_interests()

if not interests:
    st.info('No interests yet. Add some above!')
else:
    for interest in interests:
        col_name, col_status, col_actions = st.columns([2, 1, 1])
        with col_name:
            badge = '[AI]' if interest['source'] == 'llm' else '[Manual]'
            st.markdown(f"{badge} **{interest['topic']}**")
        with col_status:
            status = interest['status']
            if status == 'active':
                st.success('Active')
            else:
                st.warning('Paused')
        with col_actions:
            if interest['status'] == 'active':
                if st.button('Pause', key=f"pause_{interest['id']}"):
                    db.update_interest(interest['id'], status='paused')
                    st.rerun()
            else:
                if st.button('Activate', key=f"activate_{interest['id']}"):
                    db.update_interest(interest['id'], status='active')
                    st.rerun()
            if st.button('Delete', key=f"delete_{interest['id']}"):
                db.delete_interest(interest['id'])
                st.rerun()
