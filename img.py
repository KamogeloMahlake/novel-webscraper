import requests
import os
import psycopg2

psql = psycopg2.connect(
    host="localhost",
    database="novels",
    user="kamogelo",
    password="Shaunmah",
    port="5432",
)

cursor = psql.cursor()

cursor.execute("SELECT title, id FROM novel_novel WHERE novel_image = 'NULL'")
novels = cursor.fetchall()

for novel in novels:
    try:
        title = (
            novel[0]
            .replace(" ", "-")
            .replace("'", "")
            .replace(":", "-")
            .replace(",", "")
            .lower()
        )
        img = f"https://novelbin.me/media/novel/{title}.jpg"

        with open(f"./media/novel-images/{novel[1]}.jpg", "wb") as f:
            img_data = requests.get(img).content
            f.write(img_data)
    except Exception as e:
        print(e)
        continue
cursor.close()
psql.close()
