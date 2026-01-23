from .scraper import Scraper
from bs4 import BeautifulSoup
from time import sleep

class NovelBin(Scraper):
    """
    Scraper for NovelBin novels.
    
    Inherits from Scraper and provides methods to search, fetch metadata,
    and scrape chapter content from novelbin.me.
    """
    def __init__(self, rate_limit=2):
        """Initialize NovelBin scraper with base URL."""
        super().__init__(rate_limit)
        self.base_url = "https://novelbin.me"
        self.last_chapter_scraped = None

    def search(self, keyword):
        """
        Search for novels by keyword on NovelBin.
        
        Args:
            keyword (str): The search keyword.
            
        Returns:
            str: The URL of the selected novel.
        """
        url = f"{self.base_url}/search?keyword={keyword.replace(' ', '+')}"
        reponse = self.retry_fetch(url)
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
        reponse = self.retry_fetch(url)
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

    def story(self, url=None):
        """
        Fetch an entire novel including metadata and all chapters.
        
        Prompts user for search keyword and fetches all available chapters.
        
        Returns:
            dict: Dictionary with 'metadata' and 'chapters' keys, or None if user exits.
        """
        if url is None:
            keyword = input(
            "Enter a keyword to search for novels (or type 'exit' to quit): "
            )
            if keyword.lower() == 'exit':
                return None
            metadata, next_chapter = self.metadata(self.search(keyword))

        else:
            metadata, next_chapter = self.metadata(url)
        self.last_chapter_scraped = None

        chapter_num = 0
        chapters = []
        sleep(self.rate_limit)

        while True:
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
        print(f"{self.last_chapter_scraped} was the last chapter found.")
        return {"metadata": metadata, "chapters": chapters, "last_chapter_scraped": self.last_chapter_scraped}
    
    def chapter(self, url, chapter_num):
        """
        Fetch a specific chapter from a novel.
        
        Args:
            url (str): The chapter URL.
            chapter_num (int): The current chapter number.
            
        Returns:
            tuple: A tuple containing (next_chapter element, chapter_num, title, content).
        """
        try:
            page = self.retry_fetch(url)
        except Exception:
            raise ValueError("Chapter not found")
        soup = BeautifulSoup(page, "html.parser")
        content = soup.find("div", id="chr-content").get_text(separator="\n")
        
        try:
            title = soup.find("span", class_="chr-text").getText(strip=True)
        except TypeError:
            title = soup.find("h2").getText(strip=True)

        chapter_num += 1
        self.last_chapter_scraped = url
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

    def update(self, last_chapter_url, last_chapter_number):
        """
        Check for and fetch new chapters added to a novel since the last scrape.
        
        Args:
            last_chapter_url (str): The URL of the last chapter scraped.
            last_chapter_number (int): The last chapter number that was scraped.
        Returns:
            tuple: A tuple containing (list of new chapters, last_chapter_scraped element).
        """
        self.last_chapter_scraped = None
        page = self.retry_fetch(last_chapter_url)
        soup = BeautifulSoup(page, "html.parser")
        next_chapter = soup.find("a", id="next_chap")
        new_chapters = []

        sleep(self.rate_limit)
        
        while True:

            try:
                if "/null" in next_chapter["href"]:
                    print("No new chapters found.")
                    break

                next_chapter, last_chapter_number, title, content = self.chapter(
                    next_chapter["href"], last_chapter_number
                )
                print(f"Fetched new chapter {last_chapter_number}: {title}")
                sleep(self.rate_limit)
                new_chapters.append((str(last_chapter_number), title, content))
            except Exception as e:
                print(f"{e}")
                break
        return new_chapters, self.last_chapter_scraped