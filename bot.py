import discord
import os
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
import feedparser
import asyncio
import aiohttp
import json
import random
from datetime import datetime, timedelta, timezone
import hashlib

import asterodb

# Charger les variables d'environnement (.env)
load_dotenv()

print("Lancement du bot...")

variantes_poire = ["poire", "pear", "pera", "eriop", "birne", "🍐"]
mots_interdits = ["abruti","fdp","pute","salope","batard","ntm","enculé","connard","connards","putes","salopes","batards","nsm","nique","niquer","abrutis","enculés","niquez","niques"]

# Dictionnaire des emojis → rôles
EMOJI_ROLE_MAP = {
    "🔔": int(os.getenv("ROLE_NOTIF_TWITCH")),
    "👥": int(os.getenv("ROLE_NOTIF_COLLEGUE")),
    "✅": int(os.getenv("ROLE_MEMBRE")),
}

# Dictionnaire des messages → emojis autorisés
MESSAGE_EMOJIS = {
    int(os.getenv("MSG_REGLES")): ["✅"],
    int(os.getenv("MSG_ROLE")): ["🔔", "👥"],
}

# Mapping des chaînes YouTube
yt_channels = {
    os.getenv("ID_AKKUN7"): [
        (int(os.getenv("YT_AKKUN")), "everyone"),
        (int(os.getenv("YT_AKKUN_F")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE_F')}>")
    ],
    os.getenv("ID_AKKUN7VOD"): [
        (int(os.getenv("YT_VOD")), f"<@&{os.getenv('ROLE_NOTIF_TWITCH')}>")
    ],
    os.getenv("ID_CORENTINLEDEV"): [
        (int(os.getenv("YT_DEV")), "everyone")
    ],
    os.getenv("ID_FALNIX"): [
        (int(os.getenv("YT_FALNIX")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE')}>"),
        (int(os.getenv("YT_FALNIX_F")), "everyone")
    ],
    os.getenv("ID_RAPH"): [
        (int(os.getenv("TW_RAPH")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE')}>"),
        (int(os.getenv("TW_RAPH_F")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE_F')}>")
    ]
}

# Mapping des chaînes Twitch
twitch_streamers = {
    "akkun752": [
        (int(os.getenv("TW_AKKUN")), "@everyone"),
        (int(os.getenv("YT_AKKUN_F")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE_F')}>")
    ],
    "falnix_": [
        (int(os.getenv("YT_FALNIX")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE')}>"),
        (int(os.getenv("TW_FALNIX_F")), f"<@&{os.getenv('ROLE_NOTIF_TWITCH_F')}>")
    ],
    "rapha_aile_": [
        (int(os.getenv("TW_RAPH")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE')}>"),
        (int(os.getenv("TW_RAPH_F")), f"<@&{os.getenv('ROLE_NOTIF_COLLEGUE_F')}>")
    ]
}

# Charger les dernières vidéos depuis un fichier au lancement
if os.path.exists("last_videos.json"):
    with open("last_videos.json", "r", encoding="utf-8") as f:
        try:
            last_video_ids = json.load(f)
        except json.JSONDecodeError:
            last_video_ids = {}
else:
    last_video_ids = {}


async def check_youtube():
    await bot.wait_until_ready()
    while True:
        for channel_id, salons in yt_channels.items():
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue

            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid

            # Initialise si la chaîne n'a pas encore d'entrée
            if channel_id not in last_video_ids:
                last_video_ids[channel_id] = {}

            # 🔁 Pour chaque salon associé à cette chaîne YouTube
            for salon_id, mention_type in salons:
                if last_video_ids[channel_id].get(str(salon_id)) != video_id:
                    last_video_ids[channel_id][str(salon_id)] = video_id

                    # Sauvegarde immédiate dans le fichier JSON
                    with open("last_videos.json", "w", encoding="utf-8") as f:
                        json.dump(last_video_ids, f, indent=2, ensure_ascii=False)

                    salon = bot.get_channel(salon_id)
                    if salon:
                        # Vérifie que la vidéo n'a pas déjà été postée récemment
                        already_posted = False
                        async for message in salon.history(limit=20):
                            if latest_video.link in message.content:
                                already_posted = True
                                break

                        if not already_posted:
                            # Définir la mention à envoyer
                            mention = (
                                "||@everyone||\n" if mention_type == "everyone"
                                else ("" if mention_type == "none"
                                else f"||{mention_type}||\n")
                            )

                            await salon.send(
                                f"{mention}# {latest_video.title}\n{latest_video.link}"
                            )
                        else:
                            print(f"⏩ Vidéo déjà postée dans {salon.name} : {latest_video.link}")

        await asyncio.sleep(180)  # Vérifie toutes les 3 minutes



# Dernier statut connu du stream (True = en live, False = hors-ligne)
is_live = False

async def check_twitch():
    await bot.wait_until_ready()
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    # Récupérer un token global au lancement
    async def get_access_token():
        async with aiohttp.ClientSession() as session:
            url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
            async with session.post(url) as response:
                return (await response.json()).get("access_token")

    access_token = await get_access_token()
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}"
    }

    # Mémoire pour éviter les spams
    streamer_status = {name: False for name in twitch_streamers}

    while True:
        async with aiohttp.ClientSession() as session:
            for streamer, salons in twitch_streamers.items():
                async with session.get(f"https://api.twitch.tv/helix/streams?user_login={streamer}", headers=headers) as response:
                    data = await response.json()

                    stream_data = data.get("data", [])
                    currently_live = bool(stream_data)

                    # === STREAM START ===
                    if currently_live and not streamer_status[streamer]:
                        streamer_status[streamer] = True
                        info = stream_data[0]

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
                            title=f"{streamer} est en direct !!",
                            description=f"Catégorie : {game}\n\n👉 [Rejoindre le live]({twitch_url})",
                            color=discord.Color.purple()
                        )
                        embed.set_image(url=thumbnail)

                        # Poster dans CHAQUE salon associé
                        for salon_id, mention in salons:
                            salon = bot.get_channel(salon_id)
                            if salon:
                                mention_text = (
                                    "||@everyone||\n" if mention == "@everyone"
                                    else "" if mention in ["none", None]
                                    else f"||{mention}||\n"
                                )
                                await salon.send(f"{mention_text}# {title}", embed=embed)

                    # === STREAM END ===
                    elif not currently_live and streamer_status[streamer]:
                        streamer_status[streamer] = False
                        for salon_id, _ in salons:
                            salon = bot.get_channel(salon_id)
                            if salon:
                                await salon.send(f"🔴 **{streamer} a terminé son live.**")

        await asyncio.sleep(60)


BANS_FILE = "temp_bans.json"

# === Fonction utilitaire pour charger les bans temporaires ===
def load_temp_bans():
    if os.path.exists(BANS_FILE):
        with open(BANS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# === Fonction utilitaire pour sauvegarder les bans temporaires ===
def save_temp_bans(bans):
    with open(BANS_FILE, "w", encoding="utf-8") as f:
        json.dump(bans, f, indent=2, ensure_ascii=False)

# === Tâche de fond pour débannir les utilisateurs ===
async def temp_ban_checker(bot):
    await bot.wait_until_ready()
    while True:
        now = datetime.now(timezone.utc).timestamp()
        bans = load_temp_bans()
        updated_bans = []

        for ban in bans:
            guild = bot.get_guild(ban["guild_id"])
            if not guild:
                updated_bans.append(ban)
                continue

            if now >= ban["unban_time"]:
                try:
                    await guild.unban(await bot.fetch_user(ban["user_id"]))
                    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
                    if logs_channel:
                        await logs_channel.send(f"🔓 {ban['user_name']} a été débanni automatiquement (ban temporaire expiré).")
                except Exception as e:
                    print(f"Erreur lors du déban de {ban['user_name']}: {e}")
            else:
                updated_bans.append(ban)

        save_temp_bans(updated_bans)
        await asyncio.sleep(30)  # Vérifie toutes les 30 secondes


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Ici on démarre la tâche en arrière-plan
        self.loop.create_task(check_youtube())
        self.loop.create_task(check_twitch())
        self.loop.create_task(temp_ban_checker(self))

# Créer le bot à partir de la classe personnalisée
bot = MyBot(command_prefix="!", intents=discord.Intents.all())

# === Événement au démarrage ===
@bot.event
async def on_ready():
    print("Bot en route !")
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="🪙 Aide mon ami Akkun"
    )

    await bot.change_presence(status=discord.Status.online, activity=activity)
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")

# === Commande /akkun ===
@bot.tree.command(name="akkun", description="Affiche les chaînes Akkun7")
async def akkun(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Les chaînes de Akkun :**\n"
        "🎥 YouTube : https://youtube.com/@Akkun7\n"
        "🎬 YouTube VOD : https://youtube.com/@Akkun7VOD\n"
        "💻 Corentin le Dev : https://youtube.com/@CorentinLeDev\n"
        "👾 Twitch : https://twitch.tv/akkun752"
    )

# === Commande /falnix ===
@bot.tree.command(name="falnix", description="Affiche les chaînes Falnix")
async def falnix(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Les chaînes de Falnix :**\n"
        "🎥 YouTube : https://youtube.com/@Falnix\n"
        "👾 Twitch : https://twitch.tv/falnix_"
    )

# === Commande /raphaaile ===
@bot.tree.command(name="raphaaile", description="Affiche les chaînes Rapha_Aile")
async def raphaaile(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Les chaînes de Rapha_Aile :**\n"
        "👾 Twitch : https://twitch.tv/rapha_aile_\n"
        "🎥 YouTube : https://youtube.com/@raphaaile\n"
        "🎬 YouTube VOD : https://youtube.com/@RaphaAileVOD"
    )

# === Commande /saphira ===
@bot.tree.command(name="saphira", description="Affiche le serveur de Saphira")
async def saphira(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Les différents liens de Saphira :**\n"
        "🤖​ Discord : https://discord.gg/xmkZcekE8J\n"
        "🌐​ Site web : https://saphira-bump.fr"
    )

# === Commande /awarn ===
@bot.tree.command(name="awarn", description="Alerte un membre")
@app_commands.default_permissions(administrator=True)
async def awarn(interaction: discord.Interaction, member: discord.Member):
    if not interaction.guild:
        await interaction.response.send_message("Erreur : impossible de récupérer le serveur.", ephemeral=True)
        return

    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    server_name = interaction.guild.name

    # Envoyer le MP au membre
    await member.send(f"Tu as reçu une alerte sur **{server_name}**.")

    # Récupérer tous les messages du salon de logs pour compter les warns de cet utilisateur
    warn_count = 0
    if logs_channel:
        async for msg in logs_channel.history(limit=None):
            if f"⚠️ {member.display_name} a reçu une alerte" in msg.content:
                warn_count += 1

        # Log de l'alerte
        await logs_channel.send(f"⚠️ {member.display_name} a reçu une alerte. (Nombre d'alertes : {warn_count + 1})")

    # Message à l'utilisateur
    await interaction.response.send_message(
        f"{member.display_name} a reçu une alerte. (Nombre d'alertes : {warn_count + 1})", ephemeral=True
    )

    # Si l'utilisateur a 4 warns ou plus, bannir temporairement 30 jours
    if warn_count + 1 >= 4:
        unban_time = (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()

        await member.send(f"⚠️ Tu as atteint 4 alertes ou plus sur **{server_name}**, tu es donc banni temporairement pendant 30 jours.")
        await member.ban(reason=f"Ban automatique après 4 alertes sur {server_name}")

        # Sauvegarder le ban temporaire
        bans = load_temp_bans()
        bans.append({
            "user_id": member.id,
            "user_name": member.display_name,
            "guild_id": interaction.guild.id,
            "unban_time": unban_time
        })
        save_temp_bans(bans)

        if logs_channel:
            await logs_channel.send(f"⛔ {member.display_name} a été banni temporairement pendant 30 jours après avoir atteint 4 alertes.")

# === Commande /aban ===
@bot.tree.command(name="aban", description="Bannir un membre")
@app_commands.default_permissions(administrator=True)
async def aban(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"⛔ {member.display_name} a été banni.")
    # Nom du serveur pour le message
    server_name = interaction.guild.name if interaction.guild else "ce serveur"
    await member.send(f"Tu as été banni de {server_name}.")
    await member.ban(reason="Un modérateur a banni cet utilisateur.")
    await interaction.response.send_message(f"{member.display_name} a été banni.", ephemeral=True)

# === Commande /akick ===
@bot.tree.command(name="akick", description="Expulser un membre")
@app_commands.default_permissions(administrator=True)
async def akick(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"🚪 {member.display_name} a été expulsé.")
    # Nom du serveur pour le message
    server_name = interaction.guild.name if interaction.guild else "ce serveur"
    await member.send(f"Tu as été expulsé de {server_name}.")
    await member.kick(reason="Un modérateur a expulsé cet utilisateur.")
    await interaction.response.send_message(f"{member.display_name} a été expulsé.", ephemeral=True)

# === Commande /embed ===
@bot.tree.command(name="embed", description="Créer un Embed")
@app_commands.default_permissions(administrator=True)
async def embed(interaction: discord.Interaction, titre: str, desc: str, soustitre: str, contenu: str):
    embed = discord.Embed(title=titre, description=desc, color=discord.Color.orange())
    embed.add_field(name=soustitre, value=contenu)
    await interaction.response.send_message(embed=embed)

# === Commande /say ===
@bot.tree.command(name="say", description="Faire parler le bot")
async def say(interaction: discord.Interaction, msg: str):
    await interaction.response.send_message(msg)

# === Événement quand un membre rejoint ===
@bot.event
async def on_member_join(member: discord.Member):
    # Vérifie que l'événement vient du bon serveur
    if member.guild and member.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        welcome_channel = bot.get_channel(int(os.getenv("WELCOME")))
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))

        # Log dans le canal défini
        if logs_channel:
            await logs_channel.send(f"👋 {member.display_name} a rejoint le serveur.")

        # Message de bienvenue
        embed = discord.Embed(
            title=f"Bienvenue {member.display_name} !",
            description="Passe un agréable moment avec nous !",
            color=discord.Color.orange()
        )
        embed.set_image(url="https://www.akkunverse.fr/astero/Astero-Welcome.png")

        if welcome_channel:
            await welcome_channel.send(embed=embed)

# === Commande /dbtest ===
@bot.tree.command(name="dbtest", description="Affiche le contenu de la table astero_yt")
@app_commands.default_permissions(administrator=True)
async def dbtest(interaction: discord.Interaction):
    rows = asterodb.get_astero_yt()

    if not rows:
        await interaction.response.send_message(
            "📭 La table **astero_yt** est vide.",
            ephemeral=True
        )
        return

    # Construction des messages (limite Discord 2000 chars)
    chunks = []
    current_chunk = ""

    for row in rows:
        # row = (id, id_serveur, id_salon, lien_chaine, id_role)
        block = (
            f"**ID** `{row[0]}`\n"
            f"• Serveur : `{row[1]}`\n"
            f"• Salon : `{row[2]}`\n"
            f"• Chaîne : {row[3]}\n"
            f"• Rôle : `{row[4] if row[4] else 'Aucun'}`\n"
            "──────────────\n"
        )

        if len(current_chunk) + len(block) > 1900:
            chunks.append(current_chunk)
            current_chunk = ""

        current_chunk += block

    if current_chunk:
        chunks.append(current_chunk)

    # Envoi
    await interaction.response.send_message(chunks[0], ephemeral=True)
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=True)

# === Commande /add_notif_yt ===
@bot.tree.command(
    name="add_notif_yt",
    description="Ajoute une notification YouTube dans la base de données"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    salon="Salon où poster la notification",
    chaine_id="ID de la chaîne YouTube (UC...)",
    role_id="ID du rôle à mentionner (laisser vide ou 'everyone')"
)
async def add_notif_yt(
    interaction: discord.Interaction,
    salon: discord.TextChannel,
    chaine_id: str,
    role_id: str = None
):
    # Sécurité
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ Cette commande doit être utilisée dans un serveur.",
            ephemeral=True
        )
        return

    id_serveur = str(interaction.guild.id)
    id_salon = str(salon.id)  # 👈 ID PROPRE, PAS <#...>

    # Normalisation du rôle
    if role_id:
        role_id = role_id.strip()
        if role_id.lower() in ["null", "none", ""]:
            role_id = None
        elif role_id.lower() == "everyone":
            role_id = "everyone"
    else:
        role_id = None

    try:
        asterodb.insert_astero_yt(
            id_serveur=id_serveur,
            id_salon=id_salon,
            lien_chaine=chaine_id,
            id_role=role_id
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erreur lors de l'insertion en base de données :\n```{e}```",
            ephemeral=True
        )
        return

    # Confirmation
    await interaction.response.send_message(
        "✅ **Notification YouTube ajoutée avec succès !**\n\n"
        f"• Serveur : `{id_serveur}`\n"
        f"• Salon : {salon.mention}\n"
        f"• Chaîne : `{chaine_id}`\n"
        f"• Rôle : `{role_id if role_id else 'Aucun'}`",
        ephemeral=True
    )


# === Gestion des réactions pour les rôles ===
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignorer les réactions du bot lui-même
    if payload.user_id == bot.user.id:
        return
    
    message_id = payload.message_id
    emoji = str(payload.emoji)

    # Vérifier que le message est dans la liste
    if message_id not in MESSAGE_EMOJIS:
        return

    # Vérifier que l'emoji correspond à ce message
    if emoji not in MESSAGE_EMOJIS[message_id]:
        # Si l'emoji n'est pas autorisé, le supprimer
        channel = bot.get_channel(payload.channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.remove_reaction(emoji, payload.member)
            except:
                pass
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    # Récupération du rôle via l'emoji
    role_id = EMOJI_ROLE_MAP.get(emoji)
    if role_id is None:
        return
    
    role = guild.get_role(role_id)
    if role is None:
        return

    await member.add_roles(role)

    # Définir le disque de couleur selon le rôle
    role_colors = {
        int(os.getenv("ROLE_MEMBRE")): "🟡",
        int(os.getenv("ROLE_NOTIF_TWITCH")): "🟣",
        int(os.getenv("ROLE_NOTIF_COLLEGUE")): "🔴"
    }
    color_disc = role_colors.get(role_id, "⚪")

    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(f"✅ {color_disc} Rôle **{role.name}** ajouté à **{member.display_name}**")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    message_id = payload.message_id
    emoji = str(payload.emoji)

    if message_id not in MESSAGE_EMOJIS:
        return

    if emoji not in MESSAGE_EMOJIS[message_id]:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    role_id = EMOJI_ROLE_MAP.get(emoji)
    if role_id is None:
        return
    
    role = guild.get_role(role_id)
    if role is None:
        return

    await member.remove_roles(role)

    # Définir le disque de couleur selon le rôle
    role_colors = {
        int(os.getenv("ROLE_MEMBRE")): "🟡",
        int(os.getenv("ROLE_NOTIF_TWITCH")): "🟣",
        int(os.getenv("ROLE_NOTIF_COLLEGUE")): "🔴"
    }
    color_disc = role_colors.get(role_id, "⚪")

    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(f"❌ {color_disc} Rôle **{role.name}** retiré à **{member.display_name}**")

# === Gestion des messages ===
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    msg = message.content.lower()

    # --- Réponse "Poire 🍐" ---
    if any(var in msg for var in variantes_poire):
        await message.channel.send("Poire 🍐")

    # --- Filtrage des mots interdits ---
    mots_message = msg.split()
    if any(mot in mots_interdits for mot in mots_message):
        try:
            await message.delete()
        except discord.Forbidden:
            print("❌ Impossible de supprimer le message (permissions manquantes).")
            return

        await message.channel.send(f"{message.author.display_name}, tu ne peux pas dire ça.", delete_after=5)
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            embed = discord.Embed(
                title=message.author.display_name,
                description=message.content,
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Message supprimé dans #{message.channel.name}")
            await logs_channel.send("🧹 Message supprimé", embed=embed)
    
    await bot.process_commands(message)


# == commande /droite ou gauche améliorée ==
@bot.tree.command(name="dog", description="Droite ou Gauche ?")
async def dog(interaction: discord.Interaction, msg: str):
    # Créer un hash du message pour avoir un "nombre pseudo-aléatoire" stable
    hash_int = int(hashlib.sha256(msg.lower().encode()).hexdigest(), 16)
    dog_result = hash_int % 100  # un nombre de 0 à 99 basé sur le message

    # Définir les tranches
    if dog_result == 0:
        result = "d'**EXTREME DROITE**"
    elif dog_result < 45:
        result = "de **DROITE**"
    elif dog_result < 55:
        result = "de **CENTRE**"
    elif dog_result == 99:
        result = "d'**EXTREME GAUCHE**"
    else:
        result = "de **GAUCHE**"
    await interaction.response.send_message(f"**{msg}**, c'est {result} !")


# === Commande /clear ===
@bot.tree.command(name="clear", description="Supprime des messages dans ce salon")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(nombre="Nombre de messages à supprimer (laisser vide pour tout supprimer)")
async def clear(interaction: discord.Interaction, nombre: int = None):
    if not interaction.channel:
        await interaction.response.send_message("Erreur : impossible de récupérer le salon.", ephemeral=True)
        return

    # Confirmer l'action auprès de l'utilisateur
    await interaction.response.defer(ephemeral=True)

    try:
        # Récupérer le salon de logs
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))

        # Si un nombre est fourni, supprimer ce nombre de messages
        if nombre is not None:
            if nombre < 1:
                await interaction.followup.send("Le nombre de messages doit être supérieur à 0.", ephemeral=True)
                return
            deleted = await interaction.channel.purge(limit=nombre)
            await interaction.followup.send(f"🗑️ {len(deleted)} messages supprimés.", ephemeral=True)

            # Log
            if logs_channel:
                await logs_channel.send(f"🗑️ {interaction.user.display_name} a supprimé {len(deleted)} messages dans #{interaction.channel.name}.")
        else:
            # Sans paramètre : supprimer tous les messages du salon
            deleted = await interaction.channel.purge()
            await interaction.followup.send("🗑️ Tous les messages du salon ont été supprimés.", ephemeral=True)

            # Log
            if logs_channel:
                await logs_channel.send(f"🗑️ {interaction.user.display_name} a purgé tous les messages dans #{interaction.channel.name}.")

    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de supprimer les messages.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Une erreur est survenue : {e}", ephemeral=True)


# === Commande /atban ===
@bot.tree.command(name="atban", description="Bannir un membre temporairement")
@app_commands.default_permissions(administrator=True)
async def atban(interaction: discord.Interaction, membre: discord.Member, jours: int):
    if jours <= 0:
        await interaction.response.send_message("⛔ La durée doit être supérieure à 0 jour(s).", ephemeral=True)
        return

    unban_time = (datetime.now(timezone.utc) + timedelta(days=jours)).timestamp()

    # Bannir le membre
    # Nom du serveur pour le message
    server_name = interaction.guild.name if interaction.guild else "ce serveur"
    await membre.send(f"Tu as été banni temporairement de {server_name} pendant {jours} jour(s).")
    await membre.ban(reason=f"Ban temporaire de {jours} jour(s) par {interaction.user.display_name}.")

    # Sauvegarder le ban temporaire
    bans = load_temp_bans()
    bans.append({
        "user_id": membre.id,
        "user_name": membre.display_name,
        "guild_id": interaction.guild.id,
        "unban_time": unban_time
    })
    save_temp_bans(bans)

    # Log
    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(f"⛔ {membre.display_name} a été banni temporairement pendant {jours} jour(s).")

    await interaction.response.send_message(f"✅ {membre.display_name} a été banni temporairement pendant {jours} jour(s).", ephemeral=True)

# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))