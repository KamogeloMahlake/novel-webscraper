from bs4 import BeautifulSoup
import cloudscraper
from datetime import datetime
from ebooklib import epub
from time import sleep


class Scraper:
    def __init__(self):
        self.rate_limit =  2
        self.parser = "html.parser"
        self.scraper = cloudscraper.create_scraper()
        self.retry_attempts = 3

    def fetch(self, url):
        response = self.scraper.get(url)
        response.raise_for_status()
        return response.content
    
    def close(self):
        self.scraper.close()

class FanfictionNet(Scraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://m.fanfiction.net"
    
    def metadata(self, story_id):
        url = f"{self.base_url}/s/{story_id}"
        reponse = self.fetch(url)
        soup = BeautifulSoup(reponse, self.parser)
        content = soup.find(id="content")
        if content is None:
            raise ValueError("Story not found")
        metadata = {
            "title": content.find("b").get_text(strip=True),
            "author": content.find("a").get_text(strip=True),
            "decription": " ",
            "img_url": None
        }
        return metadata

    def story(self):
        story_id = input(
            "Enter story ID (or type 'exit' to quit): "
        )
        if story_id.lower() == 'exit':
            return None
        for _ in range(self.retry_attempts):
            try:
                metadata = self.metadata(story_id)
                break
            except Exception as e:
                last_exception = e
                sleep(self.rate_limit)
        else:
            raise last_exception

        chapters = []
        chapter_number = 1

        sleep(self.rate_limit)
        
        while True:
            try:
                chapter_content = self.chapter(story_id, chapter_number)
                sleep(self.rate_limit)
                chapters.append((str(chapter_number), f"Chapter {chapter_number}", chapter_content))
                chapter_number += 1
            except Exception as e:
                print(f"{e}")
                break
        return {"metadata": metadata, "chapters": chapters}

    def chapter(self, story_id, chapter_number):
        url = f"{self.base_url}/s/{story_id}/{chapter_number}"
        reponse = self.fetch(url)
        
        soup = BeautifulSoup(reponse, self.parser)

        chapter = soup.find(id="storycontent")
        if chapter is None:
            raise ValueError("Chapter content not found")
        
        return str(chapter)
    
class NovelBin(Scraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://novelbin.me/"

    def search(self, keyword):
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
        return array[answer]
    
    def metadata(self, url):
        reponse = self.fetch(url)
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
        
        next_chapter = soup.find(title="READ NOW", href=True)
        return {
            "title": title,
            "author": author,
            "img_url": img,
            "description": str(desc),
        }, next_chapter

    def story(self):
        keyword = input(
            "Enter a keyword to search for novels (or type 'exit' to quit): "
        )
        if keyword.lower() == 'exit':
            return None
        try:
            metadata, next_chapter = self.metadata(self.search(keyword))
        
        except Exception as e:
            print(f"{e}")
            return
        
        chapter_num = 0
        chapters = []
        sleep(self.rate_limit)

        while next_chapter["href"]:
            try:
                next_chapter, chapter_num, title, content = self.chapter(
                next_chapter["href"], chapter_num)
                print(f"Fetched chapter {chapter_num}: {title}")
                chapters.append((str(chapter_num), title, content))
                print(f"Fetching chapter from {next_chapter['href']}")
                sleep(self.rate_limit)
            
            except Exception as e:
                print(f"{e}")
                break
        print("Scraping completed.")    

        return {"metadata": metadata, "chapters": chapters}
    
    def chapter(self, url, chapter_num):
        page = self.fetch(url)
        soup = BeautifulSoup(page, "html.parser")
        content = soup.find("div", id="chr-content").get_text(separator="\n")
        
        try:
            title = soup.find("span", class_="chr-text").getText()
        except TypeError:
            title = soup.find("h2").getText()

        chapter_num += 1
        next_chapter = soup.find("a", id="next_chap")
        
        return next_chapter, chapter_num, title, str(self.text_to_html(content))
    
    def text_to_html(self, text):
        array = text.split("\n")
        html = [f"<p>{s}</p>" for s in array]
        return "".join(html)
    