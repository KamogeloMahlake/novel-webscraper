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
    
    def metadata(self, story_id, html=False):
        """
        Extract metadata for a story from AO3.
        
        Args:
            story_id (str): The story ID on AO3.
        """
        url = f"{self.base_url}/works/{story_id}?view_adult=true&amp;view_full_work=true"

        response = self.retry_fetch(url)
        soup = BeautifulSoup(response, self.parser)
        title = soup.find("h2", class_="title heading").get_text(strip=True)
        author = soup.find("a", rel="author").get_text(strip=True)
        description = soup.find("div", class_="summary module")
        
        
        metadata = {
            "title": title,
            "author": author,
            "description": str(description),
            "img_url": None,
        }
        if html:
            return metadata, soup
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
        try:
            metadata, soup = self.metadata(story_id, html=True)
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            return None
        
        chapters = []
        chapter_number = 1

        
        while True:
            try:
                chapter_number, title, content = self.get_chapter(soup, chapter_number)
                print(f"Fetched chapter {chapter_number}: {title}")
                chapters.append((str(chapter_number), title, content))
            except ValueError:
                break

        print("Scraping completed.")
        
        return {"metadata": metadata, "chapters": chapters, "id": story_id}
    
    def get_chapter(self, soup, chapter_number):
        """
        Fetch a specific chapter from a story soup.
        
        Args:
            soup (BeautifulSoup): The BeautifulSoup object of the story page.
            chapter_number (int): The chapter number to fetch.
        Returns:
            tuple: A tuple containing (chapter_number, title, content).
        """
        chapter = soup.find("div", id=f"chapter-{chapter_number}")
        if not chapter:
            raise ValueError("Chapter not found")
        title_tag = chapter.find("h3", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else f"Chapter {chapter_number}"
        content = chapter.find("div", class_="userstuff")
        return chapter_number + 1, title, content

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

    def update(self, story_id, last_chapter_number):
        """
        Fetch new chapters from a story starting after the last scraped chapter.
        """
        try:
            _, soup = self.metadata(story_id, html=True)
        except Exception as e:
            print(f"Error fetching metadata: {e}")
            return None
        
        chapters = []
        last_chapter_number += 1
        while True:
            try:
                last_chapter_number, title, content = self.get_chapter(soup, last_chapter_number)
                print(f"Fetched chapter {last_chapter_number}: {title}")
                chapters.append((str(last_chapter_number), title, content))
            except ValueError:
                break

        print("Update completed.")
        return chapters