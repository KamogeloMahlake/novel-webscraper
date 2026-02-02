from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
import requests

load_dotenv()

def get_db_connection():
    """Establish and return a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )

psql = get_db_connection()
cursor = psql.cursor()

def close_db_connection():
    """Close the database connection."""
    cursor.close()
    psql.close()

def add_novel(novel_data, last_chapter_href=None, fanficnet_id=None, ao3_id=None) -> int:
    """
    Adds a novel to the database.
    Args:
        novel_data (dict): A dictionary containing novel metadata.
        last_chapter_href (str, optional): The href of the last chapter scraped. Defaults to None.
        fanficnet_id (str, optional): The FanFiction.net ID of the novel. Defaults to None.
        ao3_id (str, optional): The AO3 ID of the novel. Defaults to None.
    Returns:
        int: The ID of the newly added novel.
    """
    try:
        insert_novel_query = "INSERT INTO novel_novel (title, creator, date, status, views, description, last_chapter_scraped, fanfic_id, ao3_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
        
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
                str(fanficnet_id),
                str(ao3_id)
            ),
        )
        novel_id = cursor.fetchone()[0]
        psql.commit()
        
        try:
            if novel_data["img_url"]:
                with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
                    img_data = requests.get(novel_data["img_url"]).content
                    f.write(img_data)
                cursor.execute("UPDATE novel_novel SET novel_image = %s WHERE id = %s", (f"novel-images/{novel_id}.jpg", int(novel_id)))
                psql.commit()

        except Exception as e:
            print(f"Failed to download or save image for novel '{novel_data['title']}': {e}")

    except psycopg2.IntegrityError:
        psql.rollback()
        print(f"Novel '{novel_data['title']}' already exists in the database. Skipping insertion.")
        cursor.execute("SELECT id FROM novel_novel WHERE title = %s", (novel_data["title"],))
        result = cursor.fetchone()
        if result:
            novel_id = result[0]
        else:
            novel_id = None
        
    return novel_id

def add_chapter(novel_id, chapter_title, chapter_num, content):
    """
    Adds a chapter to the database for a given novel.
    Args:
        novel_id (int): The ID of the novel to which the chapter belongs.
        chapter_title (str): The title of the chapter.
        chapter_num (int): The chapter number.
        content (str): The content of the chapter.
    Returns:
        None
    """
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
        chapter_id = cursor.fetchone()[0]
        print(f"Added chapter '{chapter_title}' (Chapter {chapter_num}) to novel ID {novel_id} with ID {chapter_id}")
        psql.commit()
    except psycopg2.IntegrityError:
        psql.rollback()
        print(f"Chapter '{chapter_title}' (Chapter {chapter_num}) already exists for novel ID {novel_id}. Skipping insertion.")

def update_novel_last_chapter(novel_id, last_chapter_href):
    """
    Updates the last chapter scraped for a given novel.
    Args:
        novel_id (int): The ID of the novel to update.
        last_chapter_href (str): The href of the last chapter scraped.
    """
    cursor.execute(
        "UPDATE novel_novel SET last_chapter_scraped = %s WHERE id = %s",
        (last_chapter_href, novel_id)
    )
    psql.commit()

def update_novels(novels, kwargs):
    """
    Updates existing novels in the database by scraping new chapters.
    Args:
        novels (list): A list of tuples containing novel ID, fanfic_id, and last_chapter_scraped.
    """
    novelbin = kwargs.get("novelbin_instance", None)
    fanficnet = kwargs.get("fanficnet_instance", None)
    ao3 = kwargs.get("ao3_instance", None)
    for title, novel_id, fanfic_id, last_chapter_scraped, ao3_id in novels:
        print(f"Updating novel '{title}' (ID: {novel_id})...")
        cursor.execute("SELECT MAX(num) FROM novel_chapter WHERE novel_id = %s", (novel_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            chapter_num = result[0]
        else:
            chapter_num = 0

        if fanfic_id and fanficnet:
            chapters, fanficnet_id = fanficnet.update(fanfic_id, chapter_num)

        elif ao3_id and ao3:
            chapters, ao3_idx = ao3.update(ao3_id, chapter_num)
        elif last_chapter_scraped and novelbin:
            chapters, last_chapter_scraped = novelbin.update(last_chapter_scraped, chapter_num)
        else:
            print(f"No valid source information for novel ID {novel_id}. Skipping update.")
            continue
        
        if chapters:
            if last_chapter_scraped:
                update_novel_last_chapter(novel_id, last_chapter_scraped)
            
            for chapter_num, chapter_title, content in chapters:
                add_chapter(novel_id, chapter_title, chapter_num, content)
            print(f"Updated novel ID {novel_id} with {len(chapters)} new chapters.")
        else:
            print(f"No new chapters found for novel ID {novel_id}.")
                 