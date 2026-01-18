from .scraper import Scraper
from bs4 import BeautifulSoup
from time import sleep

class Kemono(Scraper):
    """
    Scraper for Kemono sites.
    
    Inherits from Scraper and provides methods to fetch story metadata
    and chapter content from kemono sites.
    """
    def __init__(self, rate_limit=2, service="patreon"):
        """Initialize Kemono scraper with base URL."""
        super().__init__(rate_limit)
        self.base_url = "https://kemono.cr/{service}/user/"

    def get_posts(self, user_id):
        """
        Fetch posts for a given user from Kemono.
        
        Args:
            user_id (str): The user ID on Kemono.
        """
        pass
        

    