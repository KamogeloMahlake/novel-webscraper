from .scraper import Scraper
from bs4 import BeautifulSoup
from time import sleep

class FanfictionNet(Scraper):
    """
    Scraper for FanfictionNet stories.
    
    Inherits from Scraper and provides methods to fetch story metadata
    and chapter content from fanfiction.net.
    """
    def __init__(self, rate_limit=2):
        """Initialize FanfictionNet scraper with base URL."""
        super().__init__(rate_limit)
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
        reponse = self.retry_fetch(url)
        soup = BeautifulSoup(reponse, self.parser)
        content = soup.find(id="content")
        if content is None:
            raise ValueError("Story not found")
        metadata = {
            "title": content.find("b").get_text(strip=True),
            "author": content.find("a").get_text(strip=True),
            "description": " ",
            "img_url": None
        }
        return metadata

    def story(self, story_id=None):
        """
        Fetch an entire story including metadata and all chapters.
        
        Prompts user for story ID and fetches all available chapters
        with retry logic.
        
        Returns:
            dict: Dictionary with 'metadata' and 'chapters' keys, or None if user exits.
        """
        if story_id is None:
            story_id = input(
                "Enter story ID (or type 'exit' to quit): "
            )
            if story_id.lower() == 'exit':
                return None
        metadata = self.metadata(story_id)

        chapters = []
        chapter_number = 1

        sleep(self.rate_limit)
        
        while True:
            try:
                chapter_content = self.chapter(story_id, chapter_number)
                print(f"Fetched chapter {chapter_number}")
                sleep(self.rate_limit)
                chapters.append((str(chapter_number), f"Chapter {chapter_number}", chapter_content))
                print(f"Fetching chapter {chapter_number + 1}")
                chapter_number += 1
            except Exception as e:
                print(f"{e}")
                break
        return {"metadata": metadata, "chapters": chapters, "id": story_id}

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
        reponse = self.retry_fetch(url)
        
        soup = BeautifulSoup(reponse, self.parser)

        chapter = soup.find(id="storycontent")
        if chapter is None:
            raise ValueError("Chapter content not found")
        
        return str(chapter)
    
    def update(self, story_id, last_chapter_number):
        """
        Check for and fetch new chapters added to a story since the last scrape.
        Args:
            story_id (str): The story ID.
            last_chapter_number (int): The last chapter number that was scraped.
        Returns:
            list: List of tuples containing (chapter_num, chapter_title, content) for new chapters.
        """
        new_chapters = []
        chapter_number = last_chapter_number + 1

        sleep(self.rate_limit)

        while True:
            try:
                chapter_content = self.chapter(story_id, chapter_number)
                print(f"Fetched new chapter {chapter_number}")
                sleep(self.rate_limit)
                new_chapters.append((str(chapter_number), f"Chapter {chapter_number}", chapter_content))
                print(f"Fetching chapter {chapter_number + 1}")
                chapter_number += 1
            except Exception as e:
                print(f"No more new chapters found: {e}")
                break

        return (new_chapters,)