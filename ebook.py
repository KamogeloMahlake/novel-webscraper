from ebooklib import epub
import psycopg2 
from bs4 import BeautifulSoup

def text_to_html(text):
    array = text.split("\n")
    html = [f"<p>{s}</p>" for s in array]
    return "".join(html)


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


psql = psycopg2.connect(
    host="localhost",
    database="novels",
    user="kamogelo",
    password="Shaunmah",
    port="5432"
)
cursor = psql.cursor()

def create_epub(title, chapters):
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