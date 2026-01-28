from .fanficnet import FanFicNet
from time import sleep
from bs4 import BeautifulSoup

class OldFanFicNet(FanFicNet):
    def __init__(self):
        """Initialize OldFanFicNet scraper with base URL."""
        super().__init__()
        self.old_url = "https://www.fanfiction.net"
    
    def metadata(self, story_id):
        """
        Extract metadata for a story from the old FanfictionNet site.
        
        Args:
            story_id (str): The story ID on FanfictionNet.
            
        """
        url = f"{self.old_url}/s/{story_id}"
        reponse = self.retry_fetch(url)
        soup = BeautifulSoup(reponse, self.parser)
        try:
            return {
            "title": soup.find("b", class_="xcontrast_txt").get_text(strip=True),
            "author": soup.find("a", class_="xcontrast_txt").get_text(strip=True),
            "description": soup.find("div", class_="xcontrast_txt"),
            "img_url": soup.find("img", class_="cimage")["src"]
        }
        except Exception:
            return None

    def chapter(self, story_id: int, chapter_number: int) -> str:
        """
        Fetch a specific chapter of a story from the old FanfictionNet site.
            
        Args:
            story_id (str): The story ID on FanfictionNet.
            chapter_number (int): The chapter number to fetch.
        Returns:
                    
                                    str: The content of the chapter.

        """
        url = f"{self.old_url}/s/{story_id}/{chapter_number}"
        reponse = self.retry_fetch(url)
        soup = BeautifulSoup(reponse, self.parser)
        content = soup.find(id="storytextp")
        if content is None:
            raise ValueError("Chapter not found")
        return str(content)