from src.core.novelbin import NovelBin
from src.core.fanficnet import FanfictionNet
from src.core.ao3 import AO3
from src.core.kemono import Kemono
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
        print("Choose Site to Scrape From:\n1. NovelBin\n2. FanFiction.net\n3. AO3\n4. Kemono\n5. Exit")
        choice = input("Enter 1, 2, 3, 4 or 5: ").strip()
        if choice == "1":
            scraper = NovelBin(1)

        elif choice == "2":
            scraper = FanfictionNet()

        elif choice == "3":
            scraper = AO3()

        elif choice == "4":
            scraper = Kemono()
            id = input("Enter Kemono User ID: ").strip()
            return scraper.get_posts(id)

        elif choice == "5":
            print("Exiting the program.")
            return
        
        else:    
            print("Invalid choice. Please enter 1 or 2 or 3 or 4 or 5.")
            continue
        try:
            while True:
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