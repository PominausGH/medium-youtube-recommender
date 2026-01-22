# pages/4_Reading_List.py
"""Reading List page - manage saved items and sync to Obsidian."""

import streamlit as st
from obsidian_exporter import ObsidianExporter
from datetime import datetime

st.header('Reading List')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Status tabs
tab_unread, tab_reading, tab_read, tab_archived = st.tabs([
    'Unread', 'Reading', 'Read', 'Archived'
])


def display_saved_items(status):
    """Display saved items filtered by status."""
    items = db.get_saved_items(status=status)

    if not items:
        st.info(f'No {status} items.')
        return

    for item in items:
        with st.container():
            # Thumbnail if available
            col_thumb, col_content = st.columns([1, 3])

            with col_thumb:
                if item.get('thumbnail_url'):
                    st.image(item['thumbnail_url'], width=120)

            with col_content:
                st.markdown(f"**{item['title']}**")
                st.caption(f"{item.get('source_name', 'Unknown')} | Saved: {item['saved_at'][:10]}")

                if item.get('summary'):
                    st.write(item['summary'][:150] + '...')

                # Action buttons based on status
                cols = st.columns(4)

                with cols[0]:
                    st.link_button('Open', item['url'])

                with cols[1]:
                    if status == 'unread':
                        if st.button('Start Reading', key=f"start_{item['id']}"):
                            db.update_saved_item(item['id'], status='reading')
                            st.rerun()
                    elif status == 'reading':
                        if st.button('Mark Read', key=f"read_{item['id']}"):
                            db.update_saved_item(item['id'], status='read', read_at=datetime.now().isoformat())
                            st.rerun()
                    elif status == 'read':
                        if not item.get('synced_to_obsidian'):
                            if st.button('Sync to Obsidian', key=f"sync_{item['id']}"):
                                vault_path = st.session_state.get('obsidian_vault', '/obsidian')
                                exporter = ObsidianExporter(vault_path)
                                filepath = exporter.export_item(item, item.get('notes'))
                                db.update_saved_item(item['id'], synced_to_obsidian=True)
                                st.success(f'Exported to: {filepath}')
                        else:
                            st.caption('Synced')

                with cols[2]:
                    if status != 'archived':
                        if st.button('Archive', key=f"archive_{item['id']}"):
                            db.update_saved_item(item['id'], status='archived')
                            st.rerun()

                with cols[3]:
                    if status == 'archived':
                        if st.button('Restore', key=f"restore_{item['id']}"):
                            db.update_saved_item(item['id'], status='unread')
                            st.rerun()

            st.divider()


with tab_unread:
    display_saved_items('unread')

with tab_reading:
    display_saved_items('reading')

with tab_read:
    # Bulk sync option
    read_items = db.get_saved_items(status='read')
    unsynced = [i for i in read_items if not i.get('synced_to_obsidian')]
    if unsynced:
        if st.button(f'Sync All to Obsidian ({len(unsynced)} items)'):
            vault_path = st.session_state.get('obsidian_vault', '/obsidian')
            exporter = ObsidianExporter(vault_path)
            for item in unsynced:
                exporter.export_item(item, item.get('notes'))
                db.update_saved_item(item['id'], synced_to_obsidian=True)
            st.success(f'Exported {len(unsynced)} items!')
            st.rerun()

    display_saved_items('read')

with tab_archived:
    display_saved_items('archived')
