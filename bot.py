import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import feedparser
import asyncio
import aiohttp

# Charger les variables d'environnement (.env)
load_dotenv()

print("Lancement du bot...")
#bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

variantes_poire = ["poire", "pear", "pera", "eriop", "birne", "🍐"]

# Mapping des chaînes et salons
yt_channels = {
    os.getenv("ID_AKKUN7"): int(os.getenv("YT_AKKUN")),  # Akkun7
    os.getenv("ID_AKKUN7VOD"): int(os.getenv("YT_VOD")),  # Akkun7 - VOD
    os.getenv("ID_CORENTINLEDEV"): int(os.getenv("YT_DEV"))   # Corentin le Dev
}

# Stocker la dernière vidéo publiée pour chaque chaîne
last_video_ids = {}

async def check_youtube():
    await bot.wait_until_ready()
    while True:
        for channel_id, salon_id in yt_channels.items():
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue

            latest_video = feed.entries[0]
            video_id = latest_video.yt_videoid

            # Si c'est une nouvelle vidéo
            if last_video_ids.get(channel_id) != video_id:
                last_video_ids[channel_id] = video_id
                salon = bot.get_channel(salon_id)
                if salon:
                    # Ne mentionne pas everyone si c'est la chaîne VOD
                    mention = "||@everyone||\n" if channel_id != os.getenv("ID_AKKUN7VOD") else ""
                    await salon.send(
                        f"{mention}"
                        f"# {latest_video.title}\n"
                        f"{latest_video.link}"
                    )

        await asyncio.sleep(300)  # Vérifie toutes les 5 minutes

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
                            title=f"# {title}",
                            description=f"atégorie : {game_name}\n\n👉 [Venez nombreux !]({twitch_url})",
                            color=discord.Color.purple()
                        )
                        embed.set_image(url=thumbnail_url)
                        await discord_channel.send("||@everyone||", embed=embed)

                # Live terminé
                elif not currently_live and is_live:
                    is_live = False
                    if discord_channel:
                        await discord_channel.send("🔴 Le live est terminé.")

        await asyncio.sleep(180)  # Vérifie toutes les 3 minutes

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

#@bot.tree.command(name="arules", description="Créer l'Embed des règles")
#async def arules(interaction: discord.Interaction):
#    embed = discord.Embed(
#        title="📜 Règles du Discord 📜",
#        description="📜 Règles du Serveur\n\n"
#        "Bienvenue sur mon serveur Discord ! Pour garantir une expérience agréable pour tous, merci de bien respecter les règles suivantes :\n\n"
#        "**- Pas de spam :** Évitez les messages répétitifs, les publicités non autorisées et le flood dans les canaux de discussion.\n\n"
#        "**- Pas d'insultes ni de harcèlement :** Soyez respectueux envers les autres membres. Les insultes, le harcèlement et toute forme de discours haineux ne seront pas tolérés !!\n\n"
#        "**- Contenu approprié :** Assurez-vous que tout le contenu partagé reste approprié pour tous les âges. Évitez le contenu offensant, explicite ou NSFW *(Not Safe For Work)*.\n\n"
#        "**- Pas de débats sensibles :** Évitez les débats sensibles tels que la politique ou la religion, qui peuvent entraîner des tensions inutiles.\n\n"
#        "**- Pas de partage de données personnelles :** Ne partagez pas vos informations personnelles ou celles d'autres membres sur le serveur. Protégez votre vie privée et celle des autres.\n\n"
#        "Merci de respecter ces règles pour maintenir une atmosphère conviviale et accueillante pour tous les membres du serveur. En cas de problème ou de question, n'hésitez pas à contacter l'équipe de modération.\n\n"
#        "Veuillez réagir avec ✅ à ce message pour accepter les règles et accéder au reste du serveur.\n\n"
#        "Je vous souhaite un excellent séjour dans la **Maison d'Akkun** !! Amusez-vous ! 🎉",
#        color=discord.Color.orange()
#        )
#    await interaction.response.send_message(embed=embed)

# Ajouter le rôle quand on ajoute la réaction
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id != int(os.getenv("MSG_REGLES")):
        return
    if str(payload.emoji) != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return
    role = guild.get_role(int(os.getenv("ROLE_MEMBRE")))
    if role is None:
        return
    await member.add_roles(role)
    
    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(f"✅🟡 Rôle {role.name} ajouté à {member.display_name}")

# Retirer le rôle quand on retire la réaction
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id != int(os.getenv("MSG_REGLES")):
        return
    if str(payload.emoji) != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    member = guild.get_member(payload.user_id)
    if member is None:
        return
    role = guild.get_role(int(os.getenv("ROLE_MEMBRE")))
    if role is None:
        return
    await member.remove_roles(role)
    
    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(f"❌🟡 Rôle {role.name} retiré à {member.display_name}")

# Répond "Poire 🍐" quand un utilisateur dit "poire" ou variante
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    msg = message.content.lower()
    if any(var in msg for var in variantes_poire):
        await message.channel.send("Poire 🍐")

# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))