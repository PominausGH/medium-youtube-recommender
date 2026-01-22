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

# Get counts for tabs
unread_count = len(db.get_saved_items(status='unread'))
reading_count = len(db.get_saved_items(status='reading'))
read_count = len(db.get_saved_items(status='read'))
archived_count = len(db.get_saved_items(status='archived'))

# Status tabs with counts
tab_unread, tab_reading, tab_read, tab_archived = st.tabs([
    f'Unread ({unread_count})',
    f'Reading ({reading_count})',
    f'Read ({read_count})',
    f'Archived ({archived_count})'
])


def display_saved_items(status):
    """Display saved items filtered by status."""
    items = db.get_saved_items(status=status)

    if not items:
        if status == 'unread':
            st.info('No saved items yet. Use Search to find and save content!')
        else:
            st.info(f'No {status} items.')
        return

    for item in items:
        with st.container():
            # Card-like display
            col_main, col_actions = st.columns([3, 1])

            with col_main:
                # Source badge and title
                source_name = item.get('source_name', 'Unknown')
                st.markdown(f"**{item['title']}**")
                st.caption(f"{source_name} | Saved: {item['saved_at'][:10] if item.get('saved_at') else 'Unknown'}")

                # Summary preview
                if item.get('summary'):
                    summary = item['summary']
                    if len(summary) > 200:
                        summary = summary[:200] + '...'
                    st.write(summary)

            with col_actions:
                # Open link
                if item.get('url'):
                    st.link_button('Open', item['url'], use_container_width=True)

                # Status progression buttons
                if status == 'unread':
                    if st.button('Start', key=f"start_{item['id']}", use_container_width=True):
                        db.update_saved_item(item['id'], status='reading')
                        st.rerun()
                    if st.button('Done', key=f"done_{item['id']}", use_container_width=True, type="primary"):
                        db.update_saved_item(item['id'], status='read', read_at=datetime.now().isoformat())
                        st.rerun()

                elif status == 'reading':
                    if st.button('Done', key=f"read_{item['id']}", use_container_width=True, type="primary"):
                        db.update_saved_item(item['id'], status='read', read_at=datetime.now().isoformat())
                        st.rerun()

                elif status == 'read':
                    if not item.get('synced_to_obsidian'):
                        if st.button('Sync', key=f"sync_{item['id']}", use_container_width=True):
                            vault_path = st.session_state.get('obsidian_vault', '/obsidian')
                            exporter = ObsidianExporter(vault_path)
                            try:
                                filepath = exporter.export_item(item, item.get('notes'))
                                db.update_saved_item(item['id'], synced_to_obsidian=True)
                                st.success(f'Synced!')
                            except Exception as e:
                                st.error(f'Error: {e}')
                    else:
                        st.success('Synced', icon="\u2713")

                # Archive/Restore
                if status != 'archived':
                    if st.button('Archive', key=f"archive_{item['id']}", use_container_width=True):
                        db.update_saved_item(item['id'], status='archived')
                        st.rerun()
                else:
                    if st.button('Restore', key=f"restore_{item['id']}", use_container_width=True):
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
        if st.button(f'Sync All to Obsidian ({len(unsynced)} items)', type="primary"):
            vault_path = st.session_state.get('obsidian_vault', '/obsidian')
            exporter = ObsidianExporter(vault_path)
            success = 0
            for item in unsynced:
                try:
                    exporter.export_item(item, item.get('notes'))
                    db.update_saved_item(item['id'], synced_to_obsidian=True)
                    success += 1
                except Exception:
                    pass
            st.success(f'Exported {success} items!')
            st.rerun()

    display_saved_items('read')

with tab_archived:
    display_saved_items('archived')
