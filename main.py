from src.core.novelbin import NovelBin
from src.core.fanficnet import FanfictionNet  # Ensure this module exists and is correctly defined
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
        print("Choose Site to Scrape From:\n1. NovelBin\n2. FanFiction.net\n3. Exit")
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice == "1":
            scraper = NovelBin()
        elif choice == "2":
            scraper = FanfictionNet()
        elif choice == "3":
            print("Exiting the program.")
            return
        else:    
            print("Invalid choice. Please enter 1 or 2 or 3.")
            continue
        
        while True:
            story = scraper.story()

            if story is None:
                print("Exiting the program.")
                return

            metadata = story["metadata"]
            chapters = story["chapters"]

            insert_novel_query = "INSERT INTO novel_novel (title, creator, date, status, views, description, last_chapter_scraped) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
            
            try:
                cursor.execute(
                    insert_novel_query,
                    (
                        metadata["title"],
                        metadata["author"],
                        datetime.today().strftime("%d %B %Y %H:%M"),
                        False,
                        0,
                        metadata["description"],
                        story["last_chapter_scraped"],
                    ),
                )
                psql.commit()
            except psycopg2.IntegrityError:
                psql.rollback()
                print(f"Novel '{metadata['title']}' already exists in the database. Skipping insertion.")

            cursor.execute("SELECT id FROM novel_novel WHERE title = %s", (metadata["title"],))
            novel_id = cursor.fetchone()[0]
            
            if metadata["img_url"]:
                with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
                    img_data = requests.get(metadata["img_url"]).content
                    f.write(img_data)
                cursor.execute("UPDATE novel_novel SET novel_image = %s WHERE id = %s", (f"novel-images/{novel_id}.jpg", int(novel_id)))
            
            insert_chapter_query = "INSERT INTO novel_chapter (title, num, novel_id, content, date, views) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"

            for chapter_num, chapter_title, content in chapters:        
                if novel_id:
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

            print(f"Finished scraping and storing '{metadata['title']}'. Press Enter to continue or type 'back' to return to main menu.")
            if input().strip().lower() == 'back':
                break    
                
                 
if __name__ == "__main__":
    main()
    cursor.close()
    psql.close()