"""
EPUB creation utilities and simple database-driven EPUB exporter.

This module provides helpers to convert between plain text and simple
HTML paragraphs, and a create_epub function that builds an EPUB file
from title and chapter tuples. The module also contains a small script
section that reads novels and chapters from a PostgreSQL database and
generates EPUB files for each novel.
"""
import os

from dotenv import load_dotenv
from ebooklib import epub
import psycopg2 
from bs4 import BeautifulSoup

def text_to_html(text):
    """
    Convert plain text (lines separated by newlines) into HTML paragraphs.

    Args:
        text (str): Plain text with newline characters.

    Returns:
        str: HTML string with each non-empty line wrapped in <p> tags.
    """
    array = text.split("\n")
    html = [f"<p>{s}</p>" for s in array]
    return "".join(html)


def html_to_text(html):
    """
    Extract plain text from HTML content.

    Args:
        html (str): HTML string.

    Returns:
        str: Plain text with paragraphs separated by newline characters.
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


load_dotenv()

psql = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT"),
)
cursor = psql.cursor()

def create_epub(title, chapters):
    """
    Create an EPUB file from a title and an iterable of chapters.

    Args:
        title (str): Title of the book / EPUB filename (without extension).
        chapters (iterable): Sequence of (chapter_title, chapter_content) tuples.
                             chapter_content may be plain text or HTML.

    Side effects:
        Writes an EPUB file named '{title}.epub' to the current working directory.
    """
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language('en')

    for i, (chapter_title, chapter_content) in enumerate(chapters):
        if "window.pubfuturetag" in chapter_content:
            chapter_content = text_to_html(html_to_text(chapter_content))
        chapter = epub.EpubHtml(title=chapter_title, file_name=f'chap_{i+1}.xhtml', lang='en')
        chapter.content = f'<h1>{chapter_title}</h1><p>{chapter_content}</p>'
        book.add_item(chapter)
        book.toc.append(epub.Link(f'chap_{i+1}.xhtml', chapter_title, f'chap_{i+1}'))
        book.spine.append(chapter)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(f'{title}.epub', book, {})
    print(f'Created EPUB: {title}.epub')
    

cursor.execute("SELECT id, title FROM novel_novel")
novels = cursor.fetchall()

for (id, novel_title) in novels:
    cursor.execute(
        "SELECT title, content FROM novel_chapter WHERE novel_id = %s ORDER BY num",
        (id,)
    )

    chapters = cursor.fetchall()
    create_epub(novel_title, chapters)


cursor.close()
psql.close()