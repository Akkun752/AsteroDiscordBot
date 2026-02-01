import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Connexion ----------
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_IP"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWD"),
        database=os.getenv("DB_DB"),
        cursorclass=pymysql.cursors.Cursor
    )

# ---------- INSERT ----------
def insert_astero_yt(id_serveur, id_salon, lien_chaine, id_role=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO astero_yt (id_serveur, id_salon, lien_chaine, id_role)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (id_serveur, id_salon, lien_chaine, id_role))
            conn.commit()
    finally:
        conn.close()

# ---------- SELECT / PRINT ----------
def print_astero_yt():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM astero_yt")
            rows = cursor.fetchall()

            if not rows:
                print("Table astero_yt vide.")
                return

            for row in rows:
                print(row)
    finally:
        conn.close()

def get_astero_yt():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM astero_yt")
            return cursor.fetchall()
    finally:
        conn.close()
