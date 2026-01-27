from src.core.novelbin import NovelBin
from src.core.fanficnet import FanfictionNet
from src.core.ao3 import AO3
#from src.core.kemono import Kemono
from datetime import datetime
from dotenv import load_dotenv
import os
import psycopg2
import requests

load_dotenv()

psql = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT"),
)
cursor = psql.cursor()

def main():
    while True:
        print("Choose Site to Scrape From:\n1. NovelBin\n2. FanFiction.net\n3. AO3\n4. Kemono\n5. Update\n6. Update fanfic metadata \n7. Exit")
        choice = input("Enter 1, 2, 3, 4 or 5: ").strip()
        if choice == "1":
            url = input("Enter NovelBin URL (or leave blank to search): ").strip()
            scraper = NovelBin(1)

        elif choice == "2":
            scraper = FanfictionNet()

        elif choice == "3":
            scraper = AO3()

        elif choice == "4":
            return
        elif choice == "5":
            c = input("1. Update from NovelBin last chapter scraped\n2. Update from FanFiction.net ID\nChoose update method (1 or 2): ").strip()
            if c == "1":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped FROM novel_novel WHERE last_chapter_scraped IS NOT NULL")
                novels_to_update = [(t, i, f, l) for t, i, f, l in cursor.fetchall() if len(l) > 0]
            elif c == "2":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped FROM novel_novel WHERE fanfic_id IS NOT NULL")
                novels_to_update = cursor.fetchall()
            #cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped FROM novel_novel WHERE status = FALSE")
            
            update_novels(novels_to_update)
            continue
        elif choice == "6":
            cursor.execute("SELECT id, fanfic_id FROM novel_novel WHERE fanfic_id IS NOT NULL")
            novels_to_update = cursor.fetchall()
            update_metadata(novels_to_update)
            continue
        elif choice == "7":
            print("Exiting the program.")
            return
        
        else:    
            print("Invalid choice. Please enter 1 or 2 or 3 or 4 or 5.")
            continue
        try:
            while True:
                if url and choice == "1":
                    story = scraper.story(url)
                else:
                    story = scraper.story()

                if story is None:
                    print("Exiting the program.")
                    scraper.close()
                    return

                metadata = story["metadata"]
                chapters = story["chapters"]
                last_chapter_href = story.get("last_chapter_scraped", None)
                fanficnet_id = story.get("id", None)
                
                novel_id = add_novel(metadata, last_chapter_href, fanficnet_id)

                for chapter_num, chapter_title, content in chapters:        
                    if novel_id:
                        add_chapter(novel_id, chapter_title, chapter_num, content)

                print(f"Finished scraping and storing '{metadata['title']}'. Press Enter to continue or type 'back' to return to main menu.")
                if input().strip().lower() == 'back':
                    scraper.close()
                    break
        except KeyboardInterrupt:
            print("\nScraping interrupted by user. Exiting the program.")
            scraper.close()
            return    
        
def update_metadata(novels):
    fanfic = FanfictionNet()
    for novel_id, fanfic_id in novels:
        try:

            metadata = fanfic.old_metadata(fanfic_id)
            if metadata:
                cursor.execute(
                    "UPDATE novel_novel SET description = %s WHERE id = %s",
                    (
                        str(metadata["description"]),
                        novel_id
                    )
                )
                print(metadata)
                try:
                    with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
                        img_data = requests.get(f"{fanfic.old_url}{metadata['img_url']}").content
                        f.write(img_data)
                    cursor.execute("UPDATE novel_novel SET novel_image = %s WHERE id = %s", (f"novel-images/{novel_id}.jpg", int(novel_id)))
                except Exception as e:
                    print(f"Failed to download or save image for novel ID {novel_id}: {e}")

                psql.commit()
                print(f"Updated metadata for novel ID {novel_id}.")
        except Exception as e:
            print(f"Failed to update metadata for novel ID {novel_id}: {e}")

def update_novels(novels):
    """
    Updates existing novels in the database by scraping new chapters.
    Args:
        novels (list): A list of tuples containing novel ID, fanfic_id, and last_chapter_scraped.
    """
    novelbin = NovelBin(1)
    fanficnet = FanfictionNet()
    for title, novel_id, fanfic_id, last_chapter_scraped in novels:
        print(f"Updating novel '{title}' (ID: {novel_id})...")
        cursor.execute("SELECT MAX(num) FROM novel_chapter WHERE novel_id = %s", (novel_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            chapter_num = result[0]
        else:
            chapter_num = 0
        
        if fanfic_id:
            chapters, fanficnet_id = fanficnet.update(fanfic_id, chapter_num)
        elif last_chapter_scraped:
            chapters, last_chapter_scraped = novelbin.update(last_chapter_scraped, chapter_num)
        else:
            print(f"No valid source information for novel ID {novel_id}. Skipping update.")
            continue
        if chapters:
            if last_chapter_scraped:
                cursor.execute(
                    "UPDATE novel_novel SET last_chapter_scraped = %s WHERE id = %s",
                    (last_chapter_scraped, novel_id)
                )
                psql.commit()
            for chapter_num, chapter_title, content in chapters:
                add_chapter(novel_id, chapter_title, chapter_num, content)
            print(f"Updated novel ID {novel_id} with {len(chapters)} new chapters.")
        else:
            print(f"No new chapters found for novel ID {novel_id}.")

    

def add_novel(novel_data, last_chapter_href=None, fanficnet_id=None):
    """
    Adds a novel to the database.
    Args:
        novel_data (dict): A dictionary containing novel metadata.
        last_chapter_href (str, optional): The href of the last chapter scraped. Defaults to None.
        fanficnet_id (str, optional): The FanFiction.net ID of the novel. Defaults to None.
    Returns:
        int: The ID of the newly added novel.
    """
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
    psql.commit()             
                 
if __name__ == "__main__":
    main()
    cursor.close()
    psql.close()