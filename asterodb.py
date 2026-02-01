import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_IP"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWD"),
        database=os.getenv("DB_DB"),
        cursorclass=pymysql.cursors.Cursor
    )

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

def insert_astero_tw(id_serveur, id_salon, id_twitch, id_role=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO astero_tw (id_serveur, id_salon, id_twitch, id_role)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (id_serveur, id_salon, id_twitch, id_role))
            conn.commit()
    finally:
        conn.close()

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

def print_astero_tw():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM astero_tw")
            rows = cursor.fetchall()

            if not rows:
                print("Table astero_tw vide.")
                return

            for row in rows:
                print(row)
    finally:
        conn.close()

def get_astero_tw():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM astero_tw")
            return cursor.fetchall()
    finally:
        conn.close()

def get_all_yt_notifs():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT lien_chaine, id_salon, id_role
                FROM astero_yt
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def is_yt_video_posted(lien_chaine, video_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM astero_yt_posted
                WHERE lien_chaine = %s AND id_video = %s
            """, (lien_chaine, video_id))
            return cursor.fetchone() is not None
    finally:
        conn.close()

def mark_yt_video_posted(lien_chaine, video_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO astero_yt_posted (lien_chaine, id_video)
                VALUES (%s, %s)
            """, (lien_chaine, video_id))
            conn.commit()
    finally:
        conn.close()

def get_all_tw_notifs():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id_twitch, id_salon, id_role
                FROM astero_tw
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def is_tw_stream_posted(id_twitch, stream_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM astero_tw_posted
                WHERE id_twitch = %s AND stream_id = %s
            """, (id_twitch, stream_id))
            return cursor.fetchone() is not None
    finally:
        conn.close()

def mark_tw_stream_posted(id_twitch, stream_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO astero_tw_posted (id_twitch, stream_id)
                VALUES (%s, %s)
            """, (id_twitch, stream_id))
            conn.commit()
    finally:
        conn.close()

def get_notifs_for_guild(guild_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, 'YouTube' AS type, id_salon, lien_chaine, id_role
                FROM astero_yt
                WHERE id_serveur = %s
                UNION ALL
                SELECT id, 'Twitch' AS type, id_salon, id_twitch, id_role
                FROM astero_tw
                WHERE id_serveur = %s
                ORDER BY id ASC
            """, (guild_id, guild_id))
            return cursor.fetchall()
    finally:
        conn.close()

def delete_yt_notif(guild_id, notif_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM astero_yt
                WHERE id = %s AND id_serveur = %s
            """, (notif_id, guild_id))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()

def delete_tw_notif(guild_id, notif_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM astero_tw
                WHERE id = %s AND id_serveur = %s
            """, (notif_id, guild_id))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()

def add_warn(id_membre):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO astero_warns (id_membre) VALUES (%s)",
                (id_membre)
            )
            conn.commit()
    finally:
        conn.close()

def count_warns(id_membre):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM astero_warns WHERE id_membre = %s",
                (id_membre)
            )
            return cursor.fetchone()[0]
    finally:
        conn.close()

def add_to_bans(id_membre, raison=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO astero_bans (id_membre, raison) VALUES (%s, %s)",
                (id_membre, raison)
            )
            conn.commit()
    finally:
        conn.close()

def get_all_bans():
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM astero_bans")
            return cursor.fetchall()
    finally:
        conn.close()
