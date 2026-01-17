from .scraper import Scraper
from bs4 import BeautifulSoup
from time import sleep

class AO3(Scraper):
    """
    Scraper for Archive of Our Own (AO3) stories.
    
    Inherits from Scraper and provides methods to fetch story metadata
    and chapter content from archiveofourown.org.
    """
    def __init__(self):
        """Initialize AO3 scraper with base URL."""
        super().__init__()
        self.base_url = "https://archiveofourown.org"
    
    def metadata(self, story_id):
        """
        Extract metadata for a story from AO3.
        
        Args:
            story_id (str): The story ID on AO3.
        """
        url = f"{self.base_url}/works/{story_id}"
        response = self.retry_fetch(url)
        soup = BeautifulSoup(response, self.parser)
        try:
            title = soup.find("h2", class_="title heading").get_text(strip=True)
            author = soup.find("a", rel="author").get_text(strip=True)
            description = soup.find("div", class_="summary module")
        except AttributeError:
            raise ValueError("Story not found or page structure has changed")
        
        metadata = {
            "title": title,
            "author": author,
            "description": description,
            "img_url": None
        }
        return metadata

    def story(self, story_id=None):
        """
        Fetch an entire story including metadata and all chapters.
        
        Prompts user for story ID and fetches all available chapters
        with retry logic.
        
        Returns:
            dict: Dictionary with 'metadata', 'chapters' and 'last_chapter_scraped' keys.
        """
        if story_id is None:
            story_id = input(
                "Enter story ID (or type 'exit' to quit): "
            )
            if story_id.lower() == 'exit':
                return None
        metadata = self.metadata(story_id)
        sleep(self.rate_limit)
        url = f"{self.base_url}/works/{story_id}?view_adult=true&amp;view_full_work=true"
        response = self.retry_fetch(url)
        soup = BeautifulSoup(response, self.parser)
        chapter_divs = soup.find_all("div", class_="chapter")
        chapters = []
        chapter_number = 1
        print(len(chapter_divs))
        for chapter_div in chapter_divs:
            title_tag = chapter_div.find("h3", class_="title")
            title = title_tag.get_text(strip=True) if title_tag else f"Chapter {chapter_number}"
            content = chapter_div.find("div", class_="userstuff")
            chapters.append((str(chapter_number), title, content))
            print(f"Fetched chapter {chapter_number}: {title}")
            chapter_number += 1
            sleep(self.rate_limit)
        print("Scraping completed.")
        print(metadata)
        print(len(chapters))
        
        return {"metadata": metadata, "chapters": chapters, "id": story_id}
    
    def chapter(self, url, chapter_number):
        """
        Fetch a specific chapter from a story.
        
        Args:
            url (str): The URL of the chapter to fetch.
            chapter_number (int): The chapter number to fetch.

        Returns:
            tuple: A tuple containing (next_chapter_href, chapter_number, title, content).
        """
        response = self.retry_fetch(url)
        soup = BeautifulSoup(response, self.parser)
        title = soup.find("h3", class_="title").get_text(strip=True)
        content = soup.find("div", class_="userstuff")
        next_chapter = soup.find("li", class_="next")
        next_chapter_href = f"{self.base_url}{next_chapter.find('a')['href']}" if next_chapter and next_chapter.find('a') else None
        if content is None:
            raise ValueError("Chapter not found")
        return next_chapter_href, chapter_number + 1, title, content

    def update(self, last_chapter_href, chapter_number):
        """
        Check for updates to a story since the last scraped chapter.
        
        Args:
            last_chapter_href (str): The href of the last chapter scraped.
            chapter_number (int): The chapter number to start fetching from.
        Returns:
            dict: Dictionary with 'chapters' and 'last_chapter_scraped' keys.
        """
        response = self.retry_fetch(last_chapter_href)
        soup = BeautifulSoup(response, self.parser)
        next_chapter = soup.find("li", class_="next")
        if not next_chapter or not next_chapter.find("a"):
            print("No new chapters found.")
            return {"chapters": [], "last_chapter_scraped": last_chapter_href}
        next_chapter_url = f"{self.base_url}{next_chapter.find('a')['href']}"
        chapters = []
        sleep(self.rate_limit)
        while next_chapter_url:
            try:
                last_chapter_href = next_chapter_url
                next_chapter_url, chapter_number, title, content = self.chapter(next_chapter_url, chapter_number)
                print(f"Fetched chapter {chapter_number}: {title}")
                chapters.append((str(chapter_number), title, content))
                print(f"Fetching chapter from {next_chapter_url}")
                sleep(self.rate_limit)
            except Exception as e:
                print(f"{e}")
                break

        return chapters, last_chapter_href