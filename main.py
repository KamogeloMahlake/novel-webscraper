
#Local imports
from src.core.novelbin import NovelBin
from src.core.fanficnet import FanfictionNet
from src.core.ao3 import AO3
#from src.core.kemono import Kemono
from src.helpers.database_helpers import add_novel, add_chapter, close_db_connection, update_novel_last_chapter, update_novels, psql, cursor



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
            c = input("1. Update from NovelBin last chapter scraped\n2. Update from FanFiction.net ID\n3. Update from AO3 ID\n4. Update all novels with status = FALSE\nChoose update method (1 or 2): ").strip()
            if c == "1":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped, ao3_id FROM novel_novel WHERE last_chapter_scraped IS NOT NULL AND status = FALSE")
                novels_to_update = [(t, i, f, l, a) for t, i, f, l, a in cursor.fetchall() if len(l) > 0]
            elif c == "2":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped, ao3_id FROM novel_novel WHERE fanfic_id IS NOT NULL and status = FALSE")
                novels_to_update = cursor.fetchall()
            elif c == "3":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped, ao3_id FROM novel_novel WHERE ao3_id IS NOT NULL AND status = FALSE")
                novels_to_update = cursor.fetchall()
            elif c == "4":
                cursor.execute("SELECT title, id, fanfic_id, last_chapter_scraped, ao3_id FROM novel_novel WHERE status = FALSE")
                novels_to_update = cursor.fetchall()
            else:
                print("Invalid choice.")
                continue

            update_novels(novels_to_update, {"novelbin_instance": NovelBin(1), "fanficnet_instance": FanfictionNet(), "ao3_instance": AO3()})
            continue
        elif choice == "6":
            cursor.execute("SELECT id, title FROM novel_novel WHERE status = FALSE")
            novels = cursor.fetchall()
            for id, title in novels:
                update = input(f"Mark '{title}' as completed? (y/n): ").strip().lower()
                if update == 'y':
                    cursor.execute("UPDATE novel_novel SET status = TRUE WHERE id = %s", (id,))
                    psql.commit()
                    print(f"'{title}' marked as completed.")
                    continue

        elif choice == "0":
            cursor.execute("SELECT title, id, last_chapter_scraped FROM novel_novel WHERE last_chapter_scraped IS NOT NULL AND status = FALSE")
            novels_to_update = [(t, i, l) for t, i, l in cursor.fetchall() if len(l) > 0]

            for title, novel_id, last_chapter_scraped in novels_to_update:
                up = input(f"Update last chapter scraped for '{title}({novel_id}): {last_chapter_scraped}'? (y/n): ").strip().lower()
                if up == 'y':
                    new_last_chapter = input(f"Enter new last chapter href for '{title}': ").strip()
                    update_novel_last_chapter(novel_id, new_last_chapter)
                    print(f"Updated last chapter scraped for '{title}'.")
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
                ao3_id = story.get("id", None)
                
                novel_id = add_novel(metadata, last_chapter_href, fanficnet_id, ao3_id)

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
        


if __name__ == "__main__":
    main()
    close_db_connection()