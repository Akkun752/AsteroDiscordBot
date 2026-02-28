import discord
import os
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
import asyncio
import feedparser
import aiohttp
import random

import astero_db
import astero_notifs
import astero_moderation
import astero_commands
import astero_rolereacts
import astero_welcome
import astero_logs
from astero_logs import log_action, send_log

load_dotenv()

# Configuration
VERSION = "v4.2.5"
NOTIF_DELAY = 30
print(f"Lancement du bot Astero {VERSION}...")

# --- Configuration du dossier de Logs ---
if not os.path.exists("logs"):
    os.makedirs("logs")

async def check_youtube():
    await bot.wait_until_ready()

    while True:
        try:
            rows = astero_db.get_all_yt_notifs()
            yt_map = {}
            for lien_chaine, salon_id, role in rows:
                yt_map.setdefault(lien_chaine, []).append((int(salon_id), role))
            for channel_id, targets in yt_map.items():
                try:
                    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                    feed = feedparser.parse(feed_url)
                    if not feed.entries:
                        continue
                    entry = feed.entries[0]
                    video_id = entry.yt_videoid
                    if getattr(entry, "yt_live_broadcast", "none") == "upcoming":
                        continue
                    if astero_db.is_yt_video_posted(channel_id, video_id):
                        continue
                    for salon_id, role in targets:
                        salon = bot.get_channel(salon_id)
                        if not salon:
                            continue
                        if role == "everyone":
                            mention = "||@everyone||\n"
                        elif role in [None, "none"]:
                            mention = ""
                        else:
                            mention = f"||<@&{role}>||\n"
                        await salon.send(
                            f"{mention}# {entry.title}\n{entry.link}"
                        )
                    astero_db.mark_yt_video_posted(channel_id, video_id)
                except Exception as e:
                    print(f"[YouTube] Erreur chaîne {channel_id} : {e}")
        except Exception as e:
            print(f"[YouTube] Erreur globale : {e}")
        await asyncio.sleep(NOTIF_DELAY)

async def check_twitch():
    await bot.wait_until_ready()
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    async def get_access_token(session):
        url = (
            "https://id.twitch.tv/oauth2/token"
            f"?client_id={client_id}"
            f"&client_secret={client_secret}"
            "&grant_type=client_credentials"
        )
        async with session.post(url) as response:
            data = await response.json()
            return data.get("access_token")

    async with aiohttp.ClientSession() as session:
        access_token = await get_access_token(session)
        token_refresh_counter = 0

        while True:
            try:
                # Renouveler le token toutes les ~1h (3600s / 30s = 120 cycles)
                if token_refresh_counter >= 120:
                    access_token = await get_access_token(session)
                    token_refresh_counter = 0
                    print("[Twitch] Token renouvelé.")

                headers = {
                    "Client-ID": client_id,
                    "Authorization": f"Bearer {access_token}"
                }

                rows = astero_db.get_all_tw_notifs()
                tw_map = {}
                for id_twitch, salon_id, role in rows:
                    tw_map.setdefault(id_twitch.lower(), []).append((int(salon_id), role))

                for streamer, targets in tw_map.items():
                    try:
                        async with session.get(
                            f"https://api.twitch.tv/helix/streams?user_login={streamer}",
                            headers=headers
                        ) as response:
                            data = await response.json()

                        # Token expiré → on renouvelle immédiatement
                        if response.status == 401:
                            print("[Twitch] Token expiré, renouvellement...")
                            access_token = await get_access_token(session)
                            token_refresh_counter = 0
                            continue

                        stream_data = data.get("data", [])
                        if not stream_data:
                            continue
                        info = stream_data[0]
                        stream_id = info["id"]
                        if astero_db.is_tw_stream_posted(streamer, stream_id):
                            continue
                        title = info["title"]
                        game = info.get("game_name", "Jeu inconnu")
                        thumbnail = (
                            info["thumbnail_url"]
                                .replace("{width}", "1280")
                                .replace("{height}", "720")
                            + f"?cache={random.randint(100000, 999999)}"
                        )
                        twitch_url = f"https://twitch.tv/{streamer}"
                        embed = discord.Embed(
                            title=f"`{streamer}` est en direct 🟣",
                            description=f"🎮 {game}\n\n👉 [Rejoindre le live]({twitch_url})",
                            color=discord.Color.purple()
                        )
                        embed.set_image(url=thumbnail)
                        for salon_id, role in targets:
                            salon = bot.get_channel(salon_id)
                            if not salon:
                                continue
                            if role == "everyone":
                                mention = "||@everyone||\n"
                            elif role in [None, "none"]:
                                mention = ""
                            else:
                                mention = f"||<@&{role}>||\n"
                            await salon.send(f"{mention}# {title}", embed=embed)
                        astero_db.mark_tw_stream_posted(streamer, stream_id)
                    except Exception as e:
                        print(f"[Twitch] Erreur streamer {streamer} : {e}")

            except Exception as e:
                print(f"[Twitch] Erreur globale : {e}")

            token_refresh_counter += 1
            await asyncio.sleep(NOTIF_DELAY)

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_index = 0
        # Exposé sur le bot pour rétrocompatibilité si besoin
        self.log_action = log_action

    async def setup_hook(self):
        self.loop.create_task(check_youtube())
        self.loop.create_task(check_twitch())
        # Chargement des modules (Cogs)
        await astero_notifs.setup(self)
        await astero_moderation.setup(self)
        await astero_commands.setup(self)
        await astero_welcome.setup(self)
        await astero_rolereacts.setup(self)
        await astero_logs.setup(self)

        # Lancement de la boucle de changement de statut
        self.change_status.start()
        await self.tree.sync()

    # --- Tâche de changement de statut (toutes les 10 secondes) ---
    @tasks.loop(seconds=10)
    async def change_status(self):
        nb_serveurs = len(self.guilds)

        statuts = [
            f"⚔️ /help | {nb_serveurs} serveurs",
            f"⚔️ /help | {VERSION}",
            "⚔️ /help | by Akkun7"
        ]

        current_status = statuts[self.status_index]

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=current_status
        )
        await self.change_presence(status=discord.Status.online, activity=activity)
        self.status_index = (self.status_index + 1) % len(statuts)

    @change_status.before_loop
    async def before_change_status(self):
        await self.wait_until_ready()


bot = MyBot(command_prefix="!", intents=discord.Intents.all())


# === Événement au démarrage ===
@bot.event
async def on_ready():
    print(f"Bot en route ! Connecté sur {len(bot.guilds)} serveurs.")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")


# === Événement quand un membre rejoint ===
@bot.event
async def on_member_join(member: discord.Member):
    # Gestion du message de Bienvenue
    welcome_channel_id = astero_db.get_welcome_channel(member.guild.id)
    if welcome_channel_id:
        welcome_channel = bot.get_channel(int(welcome_channel_id))
        if welcome_channel:
            embed = discord.Embed(
                title=f"Bienvenue {member.display_name} !",
                description="Passe un agréable moment avec nous !",
                color=discord.Color.orange()
            )
            embed.set_image(url="https://www.akkunverse.fr/astero/welcome.png")
            await welcome_channel.send(embed=embed)

    # Gestion des Logs de join (salon + fichier)
    join_msg = f"👋 {member.mention} (`{member.display_name}`) a rejoint le serveur."
    await send_log(
        bot, member.guild.id,
        message=join_msg,
        user=str(member),
        action=f"member_join → {member.display_name} ({member.id}) sur {member.guild.name}"
    )

# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))
