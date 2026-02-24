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
            cursor.execute("""
                INSERT INTO astero_yt (id_serveur, id_salon, lien_chaine, id_role)
                VALUES (%s, %s, %s, %s)
            """, (id_serveur, id_salon, lien_chaine, id_role))
            conn.commit()
    finally:
        conn.close()

def insert_astero_tw(id_serveur, id_salon, id_twitch, id_role=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO astero_tw (id_serveur, id_salon, id_twitch, id_role)
                VALUES (%s, %s, %s, %s)
            """, (id_serveur, id_salon, id_twitch, id_role))
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
            cursor.execute("SELECT lien_chaine, id_salon, id_role FROM astero_yt")
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
            cursor.execute("SELECT id_twitch, id_salon, id_role FROM astero_tw")
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
                FROM astero_yt WHERE id_serveur = %s
                UNION ALL
                SELECT id, 'Twitch' AS type, id_salon, id_twitch, id_role
                FROM astero_tw WHERE id_serveur = %s
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
                DELETE FROM astero_yt WHERE id = %s AND id_serveur = %s
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
                DELETE FROM astero_tw WHERE id = %s AND id_serveur = %s
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
                "INSERT INTO astero_warns (id_membre) VALUES (%s)", (id_membre,)
            )
            conn.commit()
    finally:
        conn.close()

def count_warns(id_membre):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM astero_warns WHERE id_membre = %s", (id_membre,)
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

# ============================================================
# === Role Reacts ============================================
# ============================================================

# SQL à exécuter une fois pour créer la table :
# CREATE TABLE astero_rolereacts (
#     id          INT AUTO_INCREMENT PRIMARY KEY,
#     id_serveur  VARCHAR(20) NOT NULL,
#     id_message  VARCHAR(20) NOT NULL,
#     emoji       VARCHAR(100) NOT NULL,
#     id_role     VARCHAR(20) NOT NULL
# );

def insert_role_react(id_serveur, id_message, emoji, id_role):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO astero_rolereacts (id_serveur, id_message, emoji, id_role)
                VALUES (%s, %s, %s, %s)
            """, (str(id_serveur), str(id_message), emoji, str(id_role)))
            conn.commit()
    finally:
        conn.close()

def get_role_reacts_for_guild(id_serveur):
    """Retourne toutes les entrées (id, id_message, emoji, id_role) du serveur."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, id_message, emoji, id_role
                FROM astero_rolereacts
                WHERE id_serveur = %s
                ORDER BY id ASC
            """, (str(id_serveur),))
            return cursor.fetchall()
    finally:
        conn.close()

def get_role_react_by_message_and_emoji(id_message, emoji):
    """Retourne (id_serveur, id_role) pour un message+emoji donné, ou None."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id_serveur, id_role
                FROM astero_rolereacts
                WHERE id_message = %s AND emoji = %s
            """, (str(id_message), emoji))
            return cursor.fetchone()
    finally:
        conn.close()

def delete_role_react(id_serveur, react_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM astero_rolereacts
                WHERE id = %s AND id_serveur = %s
            """, (react_id, str(id_serveur)))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()

# ============================================================
# === Welcome ================================================
# ============================================================

# SQL à exécuter une fois pour créer la table :
# CREATE TABLE astero_welcome (
#     id         INT AUTO_INCREMENT PRIMARY KEY,
#     id_serveur VARCHAR(20) NOT NULL UNIQUE,
#     id_salon   VARCHAR(20) NOT NULL
# );

def set_welcome_channel(id_serveur, id_salon):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO astero_welcome (id_serveur, id_salon)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id_salon = VALUES(id_salon)
            """, (str(id_serveur), str(id_salon)))
            conn.commit()
    finally:
        conn.close()

def remove_welcome_channel(id_serveur):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM astero_welcome WHERE id_serveur = %s
            """, (str(id_serveur),))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()

def get_welcome_channel(id_serveur):
    """Retourne l'id_salon (str) du salon de bienvenue du serveur, ou None."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id_salon FROM astero_welcome WHERE id_serveur = %s
            """, (str(id_serveur),))
            row = cursor.fetchone()
            return row[0] if row else None
    finally:
        conn.close()

# === GESTION DES LOGS ===

def set_logs_channel(id_serveur, id_salon):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO astero_logs (id_serveur, id_salon) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id_salon = %s"
            cursor.execute(query, (str(id_serveur), str(id_salon), str(id_salon)))
            conn.commit()
    finally:
        conn.close()

def get_logs_channel(id_serveur):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT id_salon FROM astero_logs WHERE id_serveur = %s"
            cursor.execute(query, (str(id_serveur),))
            result = cursor.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def remove_logs_channel(id_serveur):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = "DELETE FROM astero_logs WHERE id_serveur = %s"
            cursor.execute(query, (str(id_serveur),))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()

# === GESTION DES FILTRES DE SALON ===

def add_channel_filter(id_serveur, id_salon, texte):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # On utilise un REPLACE ou INSERT ON DUPLICATE pour n'avoir qu'un filtre par salon
            query = "INSERT INTO astero_filters (id_serveur, id_salon, texte) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE texte = %s"
            cursor.execute(query, (str(id_serveur), str(id_salon), texte, texte))
            conn.commit()
    finally:
        conn.close()

def get_filters(id_serveur):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, id_salon, texte FROM astero_filters WHERE id_serveur = %s", (str(id_serveur),))
            return cursor.fetchall()
    finally:
        conn.close()

def delete_filter(id_serveur, filter_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM astero_filters WHERE id_serveur = %s AND id = %s", (str(id_serveur), filter_id))
            count = cursor.rowcount
            conn.commit()
            return count > 0
    finally:
        conn.close()

def get_filter_for_channel(id_salon):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT texte FROM astero_filters WHERE id_salon = %s", (str(id_salon),))
            row = cursor.fetchone()
            return row[0] if row else None
    finally:
        conn.close()