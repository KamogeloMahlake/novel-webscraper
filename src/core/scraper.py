"""
Web scraper module for extracting novel content from various sources.

This module provides classes for scraping novels from different websites,
including FanfictionNet and NovelBin. It handles fetching, parsing, and
organizing chapter content into structured formats.
"""
import cloudscraper
from time import sleep
from fake_useragent import UserAgent

class Scraper:
    """
    Base scraper class for fetching and parsing web content.
    
    Attributes:
        rate_limit (int): Delay in seconds between requests to avoid rate limiting.
        parser (str): HTML parser to use with BeautifulSoup.
        scraper: Cloudscraper instance for handling JavaScript-heavy sites.
        retry_attempts (int): Number of retry attempts for failed requests.
    """
    def __init__(self, rate_limit=2):
        """Initialize the base scraper with default settings."""
        self.rate_limit = rate_limit
        self.parser = "html.parser"
        self.headers = {
            "User-Agent": UserAgent().random
        }
        self.scraper = cloudscraper.create_scraper(
            interpreter='js2py',
            delay=5,
           
            browser='chrome',
            debug=False

        )
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
        response = self.scraper.get(url, headers=self.headers)
        response.raise_for_status()
        return response.content
    
    def retry_fetch(self, url):
        """
        Fetch content from a URL with retry logic.
        
        Args:
            url (str): The URL to fetch.
            
        Returns:
            bytes: The response content.
            
        Raises:
            Exception: If all retry attempts fail.
        """
        for _ in range(self.retry_attempts):
            try:
                return self.fetch(url)
            except Exception as e:
                print(f"Attempt failed: {e}")
                sleep(self.rate_limit * 10)
        raise Exception("Failed to fetch URL after multiple attempts.")
    
    def close(self):
        """Close the scraper session."""
        self.scraper.close()
