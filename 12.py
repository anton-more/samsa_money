import sqlite3
from contextlib import closing

def clear_table():
    with closing(sqlite3.connect('expenses.db')) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("DELETE FROM expenses")
            conn.commit()
            print("Таблица expenses очищена")

if __name__ == "__main__":
    clear_table()
