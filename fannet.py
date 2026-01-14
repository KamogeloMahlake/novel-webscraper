import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
from ebooklib import epub
import psycopg2
from datetime import datetime 
import cloudscraper

psql = psycopg2.connect(
    host="localhost",
    database="novels",
    user="kamogelo",
    password="Shaunmah",
    port="5432"
)

cursor = psql.cursor()

class Scraper:
    def  __init__(self):
        self.base_url = "https://m.fanfiction.net"
        self.rate_limit =  2
        self.parser = "html.parser"

    def scrape_story_metadata(self, story_id):
        url = f"{self.base_url}/s/{story_id}"
        reponse = self.fetch(url)
        soup = BeautifulSoup(reponse, self.parser)
        content = soup.find(id="content")
        if content is None:
            raise ValueError("Story not found")
        metadata = {
            "title": content.find("b").get_text(strip=True),
            "author": content.find("a").get_text(strip=True),
        }
        return metadata

    def scrape_story(self, story_id, keep_html=False):
        metadata = self.scrape_story_metadata(story_id)
        chapters = []
        chapter_number = 1

        sleep(self.rate_limit)
        
        while True:
            try:
                chapter_content = self.scrape_chapter(story_id, chapter_number, keep_html)
                sleep(self.rate_limit)
                chapters.append((str(chapter_number), chapter_content))
                chapter_number += 1
            except Exception:
                break
        return {"metadata": metadata, "chapters": chapters}

    def scrape_chapter(self, story_id, chapter_number, keep_html=False):
        url = f"{self.base_url}/s/{story_id}/{chapter_number}"
        reponse = self.fetch(url)
        
        soup = BeautifulSoup(reponse, self.parser)

        chapter = soup.find(id="storycontent")
        if chapter is None:
            raise ValueError("Chapter content not found")
        
        return str(chapter) if keep_html else chapter.get_text(' ').encode('utf-8').decode('utf-8')
    
    def fetch(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.content

class WebdriverScraper(Scraper):
    def __init__(self):
        super().__init__()
        # Initialize WebDriver here if needed
        self.driver = webdriver.Chrome()

    def fetch(self, url):
        self.driver.get(url)
        return self.driver.page_source
    
class CloudscraperScraper(Scraper):
    def __init__(self):
        super().__init__()
        self.scraper = cloudscraper.create_scraper()

    def fetch(self, url):
        response = self.scraper.get(url)
        response.raise_for_status()
        return response.content
    
def main():
    story_id = input("Enter the story ID: ")
    scraper = CloudscraperScraper()

    story = scraper.scrape_story(story_id, keep_html=True)
    title = story["metadata"]["title"]
    author = story["metadata"]["author"]
    
    insert_novel = "INSERT INTO novel_novel (title, creator, date, status, views) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(
        insert_novel,
        (
            title,
            author,
            datetime.today().strftime("%d %B %Y %H:%M"),
            False,
            0
            ),
        )
    psql.commit()
    cursor.execute("SELECT id FROM novel_novel WHERE title = %s", (title,))
    novel_id = cursor.fetchone()[0]

    insert_chapter = "INSERT INTO novel_chapter (title, num, novel_id, content, date, views) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"

    for chapter_num, content in story["chapters"]:        
        if novel_id:
            cursor.execute(
                insert_chapter,
                    (
                        "Chapter " + str(chapter_num),
                        int(chapter_num),
                        novel_id,
                        str(content),
                        datetime.today().strftime("%d %B %Y %H:%M"),
                        0
                    ),
                )
            psql.commit()   
    
    cursor.close()
    psql.close()

    create_epub(title, story["chapters"])

def create_epub(title, chapters):
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    for i, (chapter_title, chapter_content) in enumerate(chapters):
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'chap_{i+1}.xhtml', lang='en')
        chapter.content = f'<h1>{chapter_title}</h1><p>{chapter_content}</p>'
        book.add_item(chapter)
        book.toc.append(epub.Link(f'chap_{i+1}.xhtml', chapter_title, f'chap_{i+1}'))
        book.spine.append(chapter)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(f'{title}.epub', book, {})

if __name__ == "__main__":
    main()