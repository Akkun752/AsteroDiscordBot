import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import feedparser
import asyncio
import aiohttp
import json


# Charger les variables d'environnement (.env)
load_dotenv()

print("Lancement du bot...")

variantes_poire = ["poire", "pear", "pera", "eriop", "birne", "🍐"]
mots_interdits = [
    "abruti",
    "fdp",
    "pute",
    "salope",
    "batard",
    "ntm",
    "enculé",
    "connard",
    "connards",
    "putes",
    "salopes",
    "batards",
    "nsm",
    "nique",
    "niquer",
    "abrutis",
    "enculés",
    "niquez",
    "niques"
]

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
    global is_live

    twitch_user = "akkun752"
    discord_channel = bot.get_channel(int(os.getenv("TW_AKKUN")))
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    # Fonction pour obtenir un token d'accès
    async def get_access_token():
        async with aiohttp.ClientSession() as session:
            url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
            async with session.post(url) as response:
                data = await response.json()
                return data.get("access_token")

    access_token = await get_access_token()
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}"
    }

    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.twitch.tv/helix/streams?user_login={twitch_user}", headers=headers) as response:
                data = await response.json()

                stream_data = data.get("data", [])
                currently_live = bool(stream_data)

                # Nouveau live détecté
                if currently_live and not is_live:
                    is_live = True
                    stream_info = stream_data[0]
                    title = stream_info["title"]
                    game_name = stream_info.get("game_name", "Jeu inconnu")
                    thumbnail_url = stream_info["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
                    twitch_url = f"https://twitch.tv/{twitch_user}"

                    if discord_channel:
                        embed = discord.Embed(
                            title="Akkun est en direct !!",
                            description=f"Catégorie : {game_name}\n\n👉 [Venez nombreux !]({twitch_url})",
                            color=discord.Color.purple()
                        )
                        embed.set_image(url=thumbnail_url)
                        await discord_channel.send(f"||@everyone||\n# {title}", embed=embed)

                # Live terminé
                elif not currently_live and is_live:
                    is_live = False
                    if discord_channel:
                        await discord_channel.send("🔴 Le live est terminé.")

        await asyncio.sleep(60)  # Vérifie toutes les minutes

class MyBot(commands.Bot):
    async def setup_hook(self):
        # Ici on démarre la tâche en arrière-plan
        self.loop.create_task(check_youtube())
        self.loop.create_task(check_twitch())

# Créer le bot à partir de la classe personnalisée
bot = MyBot(command_prefix="!", intents=discord.Intents.all())

# === Événement au démarrage ===
@bot.event
async def on_ready():
    print("Bot en route !")
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

# === Commande /awarn ===
@bot.tree.command(name="awarn", description="Alerte un membre")
async def awarn(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"⚠️ {member.display_name} a reçu une alerte.")
    await member.send("Tu as reçu une alerte.")
    await interaction.response.send_message(f"{member.display_name} a reçu une alerte.")

# === Commande /aban ===
@bot.tree.command(name="aban", description="Bannir un membre")
async def aban(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"⛔ {member.display_name} a été banni.")
    await member.send("Tu as été banni.")
    await member.ban(reason="Un modérateur a banni cet utilisateur.")
    await interaction.response.send_message(f"{member.display_name} a été banni.")

# === Commande /akick ===
@bot.tree.command(name="akick", description="Expulser un membre")
async def akick(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"🚪 {member.display_name} a été expulsé.")
    await member.send("Tu as été expulsé.")
    await member.kick(reason="Un modérateur a expulsé cet utilisateur.")
    await interaction.response.send_message(f"{member.display_name} a été expulsé.")

# === Commande /embed ===
@bot.tree.command(name="embed", description="Créer un Embed")
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

# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))