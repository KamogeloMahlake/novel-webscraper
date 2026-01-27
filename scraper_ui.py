import streamlit as st
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
from src.core.novelbin import NovelBin
from src.core.fanficnet import FanfictionNet
from src.core.ao3 import AO3

load_dotenv()

# Page configuration
st.set_page_config(page_title="Novel Scraper UI", layout="wide", initial_sidebar_state="expanded")

# Database connection
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )

def add_novel(novel_data, last_chapter_href=None, fanficnet_id=None):
    """Adds a novel to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        insert_novel_query = "INSERT INTO novel_novel (title, creator, date, status, views, description, last_chapter_scraped, fanfic_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
        
        cursor.execute(
            insert_novel_query,
            (
                novel_data["title"],
                novel_data["author"],
                datetime.today().strftime("%d %B %Y %H:%M"),
                False,
                0,
                str(novel_data["description"]),
                last_chapter_href, 
                fanficnet_id,
            ),
        )
        novel_id = cursor.fetchone()[0]
        conn.commit()
        
        try:
            if novel_data.get("img_url"):
                os.makedirs("./media/novel-images/", exist_ok=True)
                with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
                    img_data = requests.get(novel_data["img_url"]).content
                    f.write(img_data)
                cursor.execute("UPDATE novel_novel SET novel_image = %s WHERE id = %s", (f"novel-images/{novel_id}.jpg", int(novel_id)))
                conn.commit()
        except Exception as e:
            st.warning(f"Failed to download image: {e}")

        return novel_id

    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.execute("SELECT id FROM novel_novel WHERE title = %s", (novel_data["title"],))
        result = cursor.fetchone()
        novel_id = result[0] if result else None
        return novel_id
    except Exception as e:
        st.error(f"Error adding novel: {e}")
        return None
    finally:
        cursor.close()

def add_chapter(novel_id, chapter_title, chapter_num, content):
    """Adds a chapter to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        insert_chapter_query = "INSERT INTO novel_chapter (title, num, novel_id, content, date, views) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
        cursor.execute(
            insert_chapter_query,
            (
                chapter_title,
                int(chapter_num),
                novel_id,
                str(content),
                datetime.today().strftime("%d %B %Y %H:%M"),
                0
            ),
        )
        conn.commit()
    except Exception as e:
        st.error(f"Error adding chapter: {e}")
    finally:
        cursor.close()

def update_novels(novels):
    """Updates existing novels by scraping new chapters"""
    novelbin = NovelBin(1)
    fanficnet = FanfictionNet()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (title, novel_id, fanfic_id, last_chapter_scraped) in enumerate(novels):
        status_text.text(f"Updating {idx + 1}/{len(novels)}: {title}")
        progress_bar.progress((idx + 1) / len(novels))
        
        try:
            cursor.execute("SELECT MAX(num) FROM novel_chapter WHERE novel_id = %s", (novel_id,))
            result = cursor.fetchone()
            chapter_num = result[0] if result and result[0] else 0
            
            if fanfic_id:
                chapters, fanficnet_id_new = fanficnet.update(fanfic_id, chapter_num)
            elif last_chapter_scraped:
                chapters, last_chapter_scraped_new = novelbin.update(last_chapter_scraped, chapter_num)
            else:
                st.warning(f"No valid source for {title}")
                continue
                
            if chapters:
                if last_chapter_scraped:
                    cursor.execute(
                        "UPDATE novel_novel SET last_chapter_scraped = %s WHERE id = %s",
                        (last_chapter_scraped_new, novel_id)
                    )
                    conn.commit()
                
                for ch_num, ch_title, content in chapters:
                    add_chapter(novel_id, ch_title, ch_num, content)
                st.success(f"Updated {title} with {len(chapters)} new chapters")
            else:
                st.info(f"No new chapters for {title}")
        except Exception as e:
            st.error(f"Error updating {title}: {e}")
    
    cursor.close()
    status_text.text("Update complete!")

def update_metadata(novels):
    """Updates fanfic metadata"""
    fanfic = FanfictionNet()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (novel_id, fanfic_id) in enumerate(novels):
        status_text.text(f"Updating metadata {idx + 1}/{len(novels)}")
        progress_bar.progress((idx + 1) / len(novels))
        
        try:
            metadata = fanfic.old_metadata(fanfic_id)
            if metadata:
                cursor.execute(
                    "UPDATE novel_novel SET description = %s WHERE id = %s",
                    (str(metadata["description"]), novel_id)
                )
                
                try:
                    os.makedirs("./media/novel-images/", exist_ok=True)
                    with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
                        img_data = requests.get(f"{fanfic.old_url}{metadata['img_url']}").content
                        f.write(img_data)
                    cursor.execute("UPDATE novel_novel SET novel_image = %s WHERE id = %s", 
                                 (f"novel-images/{novel_id}.jpg", int(novel_id)))
                except Exception as e:
                    st.warning(f"Failed to download image for ID {novel_id}: {e}")
                
                conn.commit()
                st.success(f"Updated metadata for novel ID {novel_id}")
        except Exception as e:
            st.error(f"Error updating metadata for ID {novel_id}: {e}")
    
    cursor.close()
    status_text.text("Metadata update complete!")

# Main UI
st.title("📚 Novel Scraper UI")
st.markdown("Interactive interface for scraping and managing novels")

# Sidebar menu
with st.sidebar:
    st.header("📖 Main Menu")
    menu_option = st.radio(
        "Choose an action:",
        options=[
            "Scrape NovelBin",
            "Scrape FanFiction.net",
            "Scrape AO3",
            "Update Novels",
            "Update Metadata",
            "Database Status"
        ],
        index=0
    )

# Display selected option
if menu_option == "Scrape NovelBin":
    st.subheader("🔍 Scrape from NovelBin")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("Enter NovelBin URL (or leave blank to search):", placeholder="https://novelbin.com/...")
    with col2:
        if st.button("🔎 Search"):
            st.info("Search functionality requires user input in CLI. Please provide URL or press Scrape.")
    
    if st.button("📥 Scrape Novel", use_container_width=True, type="primary"):
        if not url:
            st.error("Please provide a URL")
        else:
            with st.spinner("Scraping novel..."):
                try:
                    scraper = NovelBin(1)
                    story = scraper.story(url)
                    
                    if story:
                        metadata = story["metadata"]
                        chapters = story["chapters"]
                        last_chapter_href = story.get("last_chapter_scraped", None)
                        
                        # Display metadata
                        st.success("✅ Novel scraped successfully!")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"### {metadata['title']}")
                            st.markdown(f"**Author:** {metadata['author']}")
                            st.markdown(f"**Chapters:** {len(chapters)}")
                            st.text_area("Description:", metadata.get('description', ''), height=150, disabled=True)
                        
                        with col2:
                            if metadata.get('img_url'):
                                try:
                                    st.image(metadata['img_url'], width=200)
                                except:
                                    st.info("Could not display cover image")
                        
                        # Save to database
                        if st.button("💾 Save to Database", use_container_width=True):
                            with st.spinner("Saving to database..."):
                                novel_id = add_novel(metadata, last_chapter_href)
                                
                                if novel_id:
                                    progress_bar = st.progress(0)
                                    for idx, (chapter_num, chapter_title, content) in enumerate(chapters):
                                        add_chapter(novel_id, chapter_title, chapter_num, content)
                                        progress_bar.progress((idx + 1) / len(chapters))
                                    
                                    st.success(f"✅ Saved novel (ID: {novel_id}) with {len(chapters)} chapters!")
                                else:
                                    st.error("Failed to save novel")
                    else:
                        st.error("Failed to scrape novel. Check URL and try again.")
                except Exception as e:
                    st.error(f"Error: {e}")

elif menu_option == "Scrape FanFiction.net":
    st.subheader("🔍 Scrape from FanFiction.net")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("Enter FanFiction.net URL:", placeholder="https://www.fanfiction.net/...")
    
    if st.button("📥 Scrape Novel", use_container_width=True, type="primary"):
        if not url:
            st.error("Please provide a URL")
        else:
            with st.spinner("Scraping novel..."):
                try:
                    scraper = FanfictionNet()
                    story = scraper.story(url)
                    
                    if story:
                        metadata = story["metadata"]
                        chapters = story["chapters"]
                        fanficnet_id = story.get("id", None)
                        
                        st.success("✅ Novel scraped successfully!")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"### {metadata['title']}")
                            st.markdown(f"**Author:** {metadata['author']}")
                            st.markdown(f"**Chapters:** {len(chapters)}")
                            st.text_area("Description:", metadata.get('description', ''), height=150, disabled=True)
                        
                        with col2:
                            if metadata.get('img_url'):
                                try:
                                    st.image(metadata['img_url'], width=200)
                                except:
                                    st.info("Could not display cover image")
                        
                        if st.button("💾 Save to Database", use_container_width=True):
                            with st.spinner("Saving to database..."):
                                novel_id = add_novel(metadata, None, fanficnet_id)
                                
                                if novel_id:
                                    progress_bar = st.progress(0)
                                    for idx, (chapter_num, chapter_title, content) in enumerate(chapters):
                                        add_chapter(novel_id, chapter_title, chapter_num, content)
                                        progress_bar.progress((idx + 1) / len(chapters))
                                    
                                    st.success(f"✅ Saved novel (ID: {novel_id}) with {len(chapters)} chapters!")
                                else:
                                    st.error("Failed to save novel")
                    else:
                        st.error("Failed to scrape novel. Check URL and try again.")
                except Exception as e:
                    st.error(f"Error: {e}")

elif menu_option == "Scrape AO3":
    st.subheader("🔍 Scrape from AO3 (Archive of Our Own)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("Enter AO3 URL:", placeholder="https://archiveofourown.org/...")
    
    if st.button("📥 Scrape Novel", use_container_width=True, type="primary"):
        if not url:
            st.error("Please provide a URL")
        else:
            with st.spinner("Scraping novel..."):
                try:
                    scraper = AO3()
                    story = scraper.story(url)
                    
                    if story:
                        metadata = story["metadata"]
                        chapters = story["chapters"]
                        
                        st.success("✅ Novel scraped successfully!")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"### {metadata['title']}")
                            st.markdown(f"**Author:** {metadata['author']}")
                            st.markdown(f"**Chapters:** {len(chapters)}")
                            st.text_area("Description:", metadata.get('description', ''), height=150, disabled=True)
                        
                        with col2:
                            if metadata.get('img_url'):
                                try:
                                    st.image(metadata['img_url'], width=200)
                                except:
                                    st.info("Could not display cover image")
                        
                        if st.button("💾 Save to Database", use_container_width=True):
                            with st.spinner("Saving to database..."):
                                novel_id = add_novel(metadata)
                                
                                if novel_id:
                                    progress_bar = st.progress(0)
                                    for idx, (chapter_num, chapter_title, content) in enumerate(chapters):
                                        add_chapter(novel_id, chapter_title, chapter_num, content)
                                        progress_bar.progress((idx + 1) / len(chapters))
                                    
                                    st.success(f"✅ Saved novel (ID: {novel_id}) with {len(chapters)} chapters!")
                                else:
                                    st.error("Failed to save novel")
                    else:
                        st.error("Failed to scrape novel. Check URL and try again.")
                except Exception as e:
                    st.error(f"Error: {e}")

elif menu_option == "Update Novels":
    st.subheader("🔄 Update Existing Novels")
    
    update_method = st.radio(
        "Choose update method:",
        options=["Update from NovelBin", "Update from FanFiction.net"]
    )
    
    if st.button("📊 Load Novels to Update", use_container_width=True, type="primary"):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if update_method == "Update from NovelBin":
            cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped FROM novel_novel WHERE last_chapter_scraped IS NOT NULL")
            novels_to_update = [(t, i, f, l) for t, i, f, l in cursor.fetchall() if len(l) > 0]
            st.info(f"Found {len(novels_to_update)} novels to update from NovelBin")
        else:
            cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped FROM novel_novel WHERE fanfic_id IS NOT NULL")
            novels_to_update = cursor.fetchall()
            st.info(f"Found {len(novels_to_update)} novels to update from FanFiction.net")
        
        cursor.close()
        
        if novels_to_update:
            if st.button("▶️ Start Update", use_container_width=True, type="primary"):
                update_novels(novels_to_update)

elif menu_option == "Update Metadata":
    st.subheader("📝 Update Novel Metadata")
    
    if st.button("📊 Load Novels with FanFic IDs", use_container_width=True, type="primary"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, fanfic_id FROM novel_novel WHERE fanfic_id IS NOT NULL")
        novels_to_update = cursor.fetchall()
        cursor.close()
        
        st.info(f"Found {len(novels_to_update)} novels to update")
        
        if novels_to_update:
            if st.button("▶️ Update Metadata", use_container_width=True, type="primary"):
                update_metadata(novels_to_update)

elif menu_option == "Database Status":
    st.subheader("📊 Database Status")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM novel_novel")
    total_novels = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM novel_chapter")
    total_chapters = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(views) FROM novel_novel")
    total_novel_views = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(views) FROM novel_chapter")
    total_chapter_views = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM novel_novel WHERE fanfic_id IS NOT NULL")
    fanficnet_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM novel_novel WHERE last_chapter_scraped IS NOT NULL AND fanfic_id IS NULL")
    novelbin_count = cursor.fetchone()[0]
    
    cursor.close()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📖 Total Novels", total_novels)
    with col2:
        st.metric("📄 Total Chapters", total_chapters)
    with col3:
        st.metric("👁️ Novel Views", f"{total_novel_views:,}")
    with col4:
        st.metric("👁️ Chapter Views", f"{total_chapter_views:,}")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🌐 FanFiction.net", fanficnet_count)
    with col2:
        st.metric("📕 NovelBin", novelbin_count)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col2:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
