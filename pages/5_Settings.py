# pages/5_Settings.py
"""Settings page - configure integrations and manage data."""

import streamlit as st
import os

st.header('Settings')

# Obsidian settings
st.subheader('Obsidian Integration')
vault_path = st.text_input(
    'Obsidian Vault Path',
    value=st.session_state.get('obsidian_vault', '/obsidian'),
    help='Path to your Obsidian vault folder'
)
if st.button('Save Vault Path'):
    st.session_state.obsidian_vault = vault_path
    st.success('Saved!')

st.divider()

# API Keys status
st.subheader('API Configuration')
openai_key = os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY', '')
github_token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN', '')

col1, col2 = st.columns(2)
with col1:
    if openai_key:
        st.success('OpenAI API Key: Configured')
    else:
        st.warning('OpenAI API Key: Not set')
        st.caption('Set OPENAI_API_KEY environment variable')

with col2:
    if github_token:
        st.success('GitHub Token: Configured')
    else:
        st.info('GitHub Token: Not set (optional)')
        st.caption('Needed for private repos')

st.divider()

# Export/Import
st.subheader('Data Management')

if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

col_export, col_import = st.columns(2)

with col_export:
    st.markdown('**Export Interests**')
    interests = db.get_interests()
    if interests:
        import json
        export_data = json.dumps([{'topic': i['topic'], 'source': i['source']} for i in interests], indent=2)
        st.download_button(
            'Download JSON',
            export_data,
            file_name='interests.json',
            mime='application/json'
        )

with col_import:
    st.markdown('**Import Interests**')
    uploaded = st.file_uploader('Upload JSON', type='json')
    if uploaded:
        import json
        try:
            data = json.load(uploaded)
            for item in data:
                db.add_interest(item['topic'], source=item.get('source', 'manual'))
            st.success(f'Imported {len(data)} interests!')
        except Exception as e:
            st.error(f'Error: {e}')

st.divider()

# Stats
st.subheader('Statistics')
interests = db.get_interests()
content = db.get_recommended_content(limit=1000)
saved = db.get_saved_items()

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.metric('Active Interests', len([i for i in interests if i['status'] == 'active']))
with col_stat2:
    st.metric('Content Found', len(content))
with col_stat3:
    st.metric('Saved Items', len(saved))
