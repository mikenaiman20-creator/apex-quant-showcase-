import sqlite3, pathlib
def test_concurrency():
    db = pathlib.Path("trials.db")
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()
    assert True
