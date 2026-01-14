"""
Web scraper module for extracting novel content from various sources.

This module provides classes for scraping novels from different websites,
including FanfictionNet and NovelBin. It handles fetching, parsing, and
organizing chapter content into structured formats.
"""
from bs4 import BeautifulSoup
import cloudscraper
from datetime import datetime
from ebooklib import epub
from time import sleep


class Scraper:
    """
    Base scraper class for fetching and parsing web content.
    
    Attributes:
        rate_limit (int): Delay in seconds between requests to avoid rate limiting.
        parser (str): HTML parser to use with BeautifulSoup.
        scraper: Cloudscraper instance for handling JavaScript-heavy sites.
        retry_attempts (int): Number of retry attempts for failed requests.
    """
    def __init__(self):
        """Initialize the base scraper with default settings."""
        self.rate_limit =  2
        self.parser = "html.parser"
        self.scraper = cloudscraper.create_scraper()
        self.retry_attempts = 3

    def fetch(self, url):
        """
        Fetch content from a given URL.
        
        Args:
            url (str): The URL to fetch.
            
        Returns:
            bytes: The response content.
            
        Raises:
            HTTPError: If the request returns an error status code.
        """
        response = self.scraper.get(url)
        response.raise_for_status()
        return response.content
    
    def close(self):
        """Close the scraper session."""
        self.scraper.close()

class FanfictionNet(Scraper):
    """
    Scraper for FanfictionNet stories.
    
    Inherits from Scraper and provides methods to fetch story metadata
    and chapter content from fanfiction.net.
    """
    def __init__(self):
        """Initialize FanfictionNet scraper with base URL."""
        super().__init__()
        self.base_url = "https://m.fanfiction.net"
    
    def metadata(self, story_id):
        """
        Extract metadata for a story from FanfictionNet.
        
        Args:
            story_id (str): The story ID on FanfictionNet.
            
        Returns:
            dict: Dictionary containing title, author, description, and image URL.
            
        Raises:
            ValueError: If the story content cannot be found.
        """
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
        """
        Fetch an entire story including metadata and all chapters.
        
        Prompts user for story ID and fetches all available chapters
        with retry logic.
        
        Returns:
            dict: Dictionary with 'metadata' and 'chapters' keys, or None if user exits.
        """
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
        """
        Fetch a specific chapter from a story.
        
        Args:
            story_id (str): The story ID.
            chapter_number (int): The chapter number to fetch.
            
        Returns:
            str: HTML string containing the chapter content.
            
        Raises:
            ValueError: If chapter content cannot be found.
        """
        url = f"{self.base_url}/s/{story_id}/{chapter_number}"
        reponse = self.fetch(url)
        
        soup = BeautifulSoup(reponse, self.parser)

        chapter = soup.find(id="storycontent")
        if chapter is None:
            raise ValueError("Chapter content not found")
        
        return str(chapter)
    
class NovelBin(Scraper):
    """
    Scraper for NovelBin novels.
    
    Inherits from Scraper and provides methods to search, fetch metadata,
    and scrape chapter content from novelbin.me.
    """
    def __init__(self):
        """Initialize NovelBin scraper with base URL."""
        super().__init__()
        self.base_url = "https://novelbin.me/"

    def search(self, keyword):
        """
        Search for novels by keyword on NovelBin.
        
        Args:
            keyword (str): The search keyword.
            
        Returns:
            str: The URL of the selected novel.
        """
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
        """
        Extract metadata for a novel from NovelBin.
        
        Args:
            url (str): The novel URL on NovelBin.
            
        Returns:
            tuple: A tuple containing (metadata dict, next_chapter element).
        """
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
        """
        Fetch an entire novel including metadata and all chapters.
        
        Prompts user for search keyword and fetches all available chapters.
        
        Returns:
            dict: Dictionary with 'metadata' and 'chapters' keys, or None if user exits.
        """
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
        """
        Fetch a specific chapter from a novel.
        
        Args:
            url (str): The chapter URL.
            chapter_num (int): The current chapter number.
            
        Returns:
            tuple: A tuple containing (next_chapter element, chapter_num, title, content).
        """
        for _ in range(self.retry_attempts):
            try:
                page = self.fetch(url)
                break
            except Exception as e:
                print(f"Attempt failed: {e}")
                sleep(self.rate_limit * 2)
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
        """
        Convert plain text to HTML paragraphs.
        
        Args:
            text (str): Plain text with newline separators.
            
        Returns:
            str: HTML string with text wrapped in <p> tags.
        """
        array = text.split("\n")
        html = [f"<p>{s}</p>" for s in array]
        return "".join(html)
