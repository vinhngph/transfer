import sqlite3
from typing import Any, Tuple


class SQL:
    def __init__(self, database_url:str) -> None:
        self.database_url = database_url

    def execute(self, query: str, args: Tuple[Any, ...] = ()):
        try:
            with sqlite3.connect(self.database_url) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, args)

                if query.strip().upper().startswith("SELECT"):
                    return [dict(row) for row in cursor.fetchall()]
                elif query.strip().upper().startswith("INSERT"):
                    conn.commit()
                    return cursor.lastrowid
                else:
                    conn.commit()
                    return None

        except sqlite3.Error as e:
            print(f"Database erro: {e}")
            return None