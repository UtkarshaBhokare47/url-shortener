from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
import random
import string
import sqlite3

app = FastAPI()

# Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------- DATABASE ----------------

def get_db_connection():
    connection = sqlite3.connect("urls.db")
    connection.row_factory = sqlite3.Row
    return connection


def create_table():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


create_table()


# ---------------- REQUEST MODEL ----------------

class URLRequest(BaseModel):
    original_url: str


# ---------------- SHORT CODE ----------------

def generate_short_code():

    characters = string.ascii_letters + string.digits

    while True:

        short_code = ""

        for i in range(6):
            short_code = short_code + random.choice(characters)

        connection = get_db_connection()

        existing = connection.execute(
            "SELECT short_code FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        connection.close()

        if existing is None:
            return short_code


# ---------------- HOME / UI ----------------

@app.get("/")
def home():
    return FileResponse("static/index.html")


# ---------------- SHORTEN URL ----------------

@app.post("/shorten")
def shorten_url(data: URLRequest):

    short_code = generate_short_code()

    connection = get_db_connection()

    connection.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, data.original_url)
    )

    connection.commit()
    connection.close()

    return {
        "original_url": data.original_url,
        "short_code": short_code,
        "short_url": f"http://127.0.0.1:8000/{short_code}"
    }


# ---------------- GET ALL URLS ----------------

@app.get("/urls")
def get_all_urls():

    connection = get_db_connection()

    urls = connection.execute(
        "SELECT * FROM urls"
    ).fetchall()

    connection.close()

    return [dict(url) for url in urls]


# ---------------- UPDATE URL ----------------

@app.put("/urls/{id}")
def update_url(id: int, data: URLRequest):

    connection = get_db_connection()

    url = connection.execute(
        "SELECT * FROM urls WHERE id = ?",
        (id,)
    ).fetchone()

    if not url:
        connection.close()
        return {"error": "URL not found"}

    connection.execute(
        "UPDATE urls SET original_url = ? WHERE id = ?",
        (data.original_url, id)
    )

    connection.commit()
    connection.close()

    return {
        "message": "URL updated successfully",
        "id": id,
        "original_url": data.original_url
    }


# ---------------- DELETE URL ----------------

@app.delete("/urls/{id}")
def delete_url(id: int):

    connection = get_db_connection()

    url = connection.execute(
        "SELECT * FROM urls WHERE id = ?",
        (id,)
    ).fetchone()

    if not url:
        connection.close()
        return {"error": "URL not found"}

    connection.execute(
        "DELETE FROM urls WHERE id = ?",
        (id,)
    )

    connection.commit()
    connection.close()

    return {
        "message": "URL deleted successfully",
        "deleted_id": id
    }


# ---------------- REDIRECT ----------------

@app.get("/{short_code}")
def redirect_url(short_code: str):

    connection = get_db_connection()

    url = connection.execute(
        "SELECT original_url FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()

    connection.close()

    if url:
        return RedirectResponse(url=url["original_url"])

    return {
        "error": "Short URL not found"
    }