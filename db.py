"""SQLite helpers."""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "tubelens.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        sql = f.read()
    conn = get_conn()
    conn.executescript(sql)
    conn.commit()
    conn.close()
    print("DB OK:", DB_PATH)


if __name__ == "__main__":
    init_db()
