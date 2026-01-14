import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime
import cloudscraper

psql = psycopg2.connect(
    host="localhost",
    database="novels",
    user="kamogelo",
    password="Shaunmah",
    port="5432",
)

cursor = psql.cursor()

class Scraper:
    def __init__(self):
        self.base_url = "https://novelbin.me/"
        self.parser = "html.parser"

    def search_stories(self, keyword):
        url = f"{self.base_url}/search?keyword={keyword.replace(' ', '+')}"
        reponse =  self.fetch(url)
        links = BeautifulSoup(reponse, "html.parser").find_all(
            "h3", class_="novel-title"
        )

        i = 0
        array = []

        for link in links:
            array.append(str(link.find("a")["href"]))
            print(f"{i}. {link.find('a').getText()}")
            i += 1

        answer = int(input("Select a novel by entering its number: "))
        return self.fetch(array[answer])
    
    def scrape_story(self, keep_html=False):
        keyword = input(
            "Enter a keyword to search for novels (or type 'exit' to quit): "
        )
        reponse = self.search_stories(keyword)
        soup = BeautifulSoup(reponse, self.parser)

        title = soup.find("h3", class_="title").getText()
        img = soup.find("img", class_="lazy")["data-src"]
        desc = soup.find("div", class_="desc-text")

        try:
            author = (
                soup.find("ul", class_="info info-meta")
                .getText()
                .split(" ")[0]
                .split("\n")[3]
            )
        except Exception:
            author = "Unknown"

        insert_novel = "INSERT INTO novel_novel (title, creator, description, date, status, views) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(
            insert_novel,
            (
                title,
                author,
                str(desc),
                datetime.today().strftime("%d %B %Y %H:%M"),
                False,
                0
            ),
        )

        psql.commit()
        cursor.execute("SELECT id FROM novel_novel WHERE title = %s", (title,))
        novel_id = cursor.fetchone()[0]

        with open(f"./media/novel-images/{novel_id}.jpg", "wb") as f:
            img_data = self.fetch(img)
            f.write(img_data)

        next_chapter = reponse.find(title="READ NOW", href=True)
        chapter_num = 0
        while next_chapter["href"]:
            try:
                next_chapter, chapter_num = self.scrape_chapter(
                next_chapter["href"], chapter_num, novel_id
            )
                print(f"Fetching chapter from {next_chapter['href']}")
            except requests.exceptions.MissingSchema:
                print("Invalid URL. Please try again.")
                break
        print("Scraping completed.")    

    def scrape_chapter(self, url, chapter_num, novel_id):
        page = self.fetch(url)
        soup = BeautifulSoup(page.text, "html.parser")
        content = soup.find("div", id="chr-content")
        try:
            title = soup.find("span", class_="chr-text").getText()
        except TypeError:
            title = soup.find("h2").getText()

        chapter_num += 1
        insert_chapter = "INSERT INTO novel_chapter (title, num, novel, content, date, views) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
        if novel_id:
            cursor.execute(
                insert_chapter,
                (
                    title,
                    chapter_num,
                    novel_id,
                    str(content),
                    datetime.today().strftime("%d %B %Y %H:%M"),
                    0
                    ),
                )
            psql.commit()
            return soup.find("a", id="next_chap"), chapter_num
        return None, chapter_num        

    def fetch(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return response.content

class CloudScraperScraper(Scraper):
    def __init__(self):
        super().__init__()
        self.scraper = cloudscraper.create_scraper()

    def fetch(self, url):
        response = self.scraper.get(url)
        response.raise_for_status()
        return response.content
    
cursor.close()
psql.close()
