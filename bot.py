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
import re

import asterodb

load_dotenv()
print("Lancement du bot...")

variantes_poire = ["poire", "pear", "pera", "eriop", "birne", "🍐"]
mots_interdits = ["abruti","fdp","pute","salope","batard","ntm","enculé","connard","connards","putes","salopes","batards","nsm","nique","niquer","abrutis","enculés","niquez","niques"]

EMOJI_ROLE_MAP = {
    "🔔": int(os.getenv("ROLE_NOTIF_TWITCH")),
    "👥": int(os.getenv("ROLE_NOTIF_COLLEGUE")),
    "✅": int(os.getenv("ROLE_MEMBRE")),
    "📅": int(os.getenv("ROLE_NOTIF_PLANNING")),
    "🛠️": int(os.getenv("ROLE_NOTIF_PROJETS")),
    "📊": int(os.getenv("ROLE_NOTIF_SONDAGES")),
}

MESSAGE_EMOJIS = {
    int(os.getenv("MSG_REGLES")): ["✅"],
    int(os.getenv("MSG_ROLE")): ["🔔", "👥","📅","🛠️","📊"],
}

async def check_youtube():
    await bot.wait_until_ready()

    while True:
        rows = asterodb.get_all_yt_notifs()
        yt_map = {}
        for lien_chaine, salon_id, role in rows:
            yt_map.setdefault(lien_chaine, []).append((int(salon_id), role))
        for channel_id, targets in yt_map.items():
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
            entry = feed.entries[0]
            video_id = entry.yt_videoid
            if getattr(entry, "yt_live_broadcast", "none") == "upcoming":
                continue
            if asterodb.is_yt_video_posted(channel_id, video_id):
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
            asterodb.mark_yt_video_posted(channel_id, video_id)
        await asyncio.sleep(180)

async def check_twitch():
    await bot.wait_until_ready()
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")
    async def get_access_token():
        async with aiohttp.ClientSession() as session:
            url = (
                "https://id.twitch.tv/oauth2/token"
                f"?client_id={client_id}"
                f"&client_secret={client_secret}"
                "&grant_type=client_credentials"
            )
            async with session.post(url) as response:
                return (await response.json()).get("access_token")
    access_token = await get_access_token()
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}"
    }
    while True:
        rows = asterodb.get_all_tw_notifs()
        tw_map = {}
        for id_twitch, salon_id, role in rows:
            tw_map.setdefault(id_twitch.lower(), []).append((int(salon_id), role))
        async with aiohttp.ClientSession() as session:
            for streamer, targets in tw_map.items():
                async with session.get(
                    f"https://api.twitch.tv/helix/streams?user_login={streamer}",
                    headers=headers
                ) as response:
                    data = await response.json()
                stream_data = data.get("data", [])
                if not stream_data:
                    continue
                info = stream_data[0]
                stream_id = info["id"]
                if asterodb.is_tw_stream_posted(streamer, stream_id):
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
                asterodb.mark_tw_stream_posted(streamer, stream_id)
        await asyncio.sleep(60)

async def check_global_bans():
    await bot.wait_until_ready()
    while True:
        bans = asterodb.get_all_bans()
        for guild in bot.guilds:
            logs_channel = bot.get_channel(int(os.getenv("LOGS")))
            for ban_entry in bans:
                member_id = ban_entry["id_membre"]
                raison = ban_entry.get("raison", "Banni automatiquement")
                member = guild.get_member(member_id)
                if member:
                    try:
                        await member.ban(reason=raison)
                        if logs_channel:
                            await logs_channel.send(
                                f"⛔ {member.mention} a été banni automatiquement sur {guild.name} ({raison})"
                            )
                    except Exception as e:
                        print(f"Erreur en bannissant {member_id} sur {guild.name} : {e}")
        await asyncio.sleep(300)  # toutes les 5 minutes

class MyBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(check_youtube())
        self.loop.create_task(check_twitch())
        self.loop.create_task(check_global_bans())
bot = MyBot(command_prefix="!", intents=discord.Intents.all())

# === Événement au démarrage ===
@bot.event
async def on_ready():
    print("Bot en route !")
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="⚔️ Défend Discord de toutes mes force !"
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
        await interaction.response.send_message(
            "Erreur : impossible de récupérer le serveur.",
            ephemeral=True
        )
        return
    id_membre = member.id
    asterodb.add_warn(id_membre)
    total_warns = asterodb.count_warns(id_membre)
    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    server_name = interaction.guild.name
    try:
        await member.send(f"⚠️ Tu as reçu une alerte sur **{server_name}**. (Total : {total_warns})")
    except Exception:
        pass
    if logs_channel:
        await logs_channel.send(
            f"⚠️ {member.mention} a reçu une alerte. (Total : {total_warns})"
        )
    await interaction.response.send_message(
        f"{member.mention} a reçu une alerte. (Total : {total_warns})",
        ephemeral=True
    )
    if total_warns >= 4:
        await member.send(
            f"⚠️ Tu as atteint 4 alertes ou plus, tu es donc banni définitivement."
        )
        await member.ban(reason=f"Ban automatique après 4 alertes")
        asterodb.add_to_bans(member.id, raison="Ban après 4 alerts")
        if logs_channel:
            await logs_channel.send(
                f"⛔ {member.mention} a été banni définitivement après avoir atteint 4 alertes."
            )

# === Commande /aban ===
@bot.tree.command(name="aban", description="Bannir un membre")
@app_commands.default_permissions(administrator=True)
async def aban(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"⛔ {member.display_name} a été banni.")
    server_name = interaction.guild.name if interaction.guild else "ce serveur"
    await member.send(f"Tu as été banni de {server_name}.")
    await member.ban(reason="Un modérateur a banni cet utilisateur.")
    asterodb.add_to_bans(member.id, raison="Ban par un modérateur")
    await interaction.response.send_message(f"{member.display_name} a été banni.", ephemeral=True)

# === Commande /akick ===
@bot.tree.command(name="akick", description="Expulser un membre")
@app_commands.default_permissions(administrator=True)
async def akick(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild and interaction.guild.id == int(os.getenv("SERVEUR_AKKUN")):
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if logs_channel:
            await logs_channel.send(f"🚪 {member.display_name} a été expulsé.")
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
        if logs_channel:
            await logs_channel.send(f"👋 {member.display_name} a rejoint le serveur.")
        embed = discord.Embed(
            title=f"Bienvenue {member.display_name} !",
            description="Passe un agréable moment avec nous !",
            color=discord.Color.orange()
        )
        embed.set_image(url="https://www.corentin-boutigny.fr/AsteroWelcome.png")
        if welcome_channel:
            await welcome_channel.send(embed=embed)

@bot.tree.command(
    name="list_notif",
    description="Liste les notifications YouTube et Twitch de ce serveur"
)
@app_commands.default_permissions(administrator=True)
async def list_notif(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    rows = asterodb.get_notifs_for_guild(guild_id)
    if not rows:
        await interaction.response.send_message(
            "📭 Aucune notification configurée sur ce serveur.",
            ephemeral=True
        )
        return
    yt_blocks = []
    tw_blocks = []
    for notif_id, type_, salon_id, identifiant, role in rows:
        salon = f"<#{salon_id}>"
        role_txt = (
            "@everyone" if role == "everyone"
            else "Aucun rôle" if not role
            else f"<@&{role}>"
        )
        block = (
            f"**{notif_id}** : `{identifiant}`\n"
            f"{salon} • {role_txt}"
        )
        if type_ == "YouTube":
            yt_blocks.append(block)
        else:
            tw_blocks.append(block)
    def build_section(title, blocks, emoji):
        if not blocks:
            return f"_Aucune notification {title.lower()}_"
        return (
            f"**{emoji} {title.upper()}**\n"
            "══════════════════\n"
            + "\n────────────\n".join(blocks)
        )
    embed = discord.Embed(
        title="📢 Notifications du serveur",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="══════════════════",
        value=build_section("YouTube", yt_blocks, "📺"),
        inline=False
    )
    embed.add_field(
        name="══════════════════",
        value=build_section("Twitch", tw_blocks, "🎮"),
        inline=False
    )
    embed.set_footer(
        text="Suppression : /remove_notif <youtube|twitch> <id>"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# === Commande /add_notif ===
@bot.tree.command(
    name="add_notif",
    description="Ajoute une notification YouTube ou Twitch"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    type="Plateforme (YouTube ou Twitch)",
    salon="Salon où poster la notification",
    identifiant="ID chaîne YouTube (UC...) ou login/ID Twitch",
    role="Rôle à mentionner (@role, ID, @everyone ou 'none')"
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Twitch", value="twitch")
    ]
)
async def add_notif(
    interaction: discord.Interaction,
    type: app_commands.Choice[str],
    salon: discord.TextChannel,
    identifiant: str,
    role: str
):
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ Cette commande doit être utilisée dans un serveur.",
            ephemeral=True
        )
        return
    id_serveur = str(interaction.guild.id)
    id_salon = str(salon.id)
    role = role.strip()
    id_role = None
    if role.lower() in ["none", "aucun", "null"]:
        id_role = None
    elif role.lower() in ["everyone", "@everyone"]:
        id_role = "everyone"

    else:
        match = re.match(r"<@&(\d+)>", role)
        if match:
            id_role = match.group(1)
        elif role.isdigit():
            id_role = role
        else:
            await interaction.response.send_message(
                "❌ Rôle invalide.\n\n"
                "Formats acceptés :\n"
                "• `@role`\n"
                "• `123456789`\n"
                "• `@everyone`\n"
                "• `none`",
                ephemeral=True
            )
            return
    try:
        if type.value == "youtube":
            asterodb.insert_astero_yt(
                id_serveur=id_serveur,
                id_salon=id_salon,
                lien_chaine=identifiant,
                id_role=id_role
            )
        else:
            asterodb.insert_astero_tw(
                id_serveur=id_serveur,
                id_salon=id_salon,
                id_twitch=identifiant,
                id_role=id_role
            )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Erreur base de données :\n```{e}```",
            ephemeral=True
        )
        return
    await interaction.response.send_message(
        "✅ **Notification ajoutée !**\n\n"
        f"• Type : **{type.name}**\n"
        f"• Salon : {salon.mention}\n"
        f"• Identifiant : `{identifiant}`\n"
        f"• Rôle : `{id_role if id_role else 'Aucun'}`",
        ephemeral=True
    )

# === Commande /remove_notif ===
@bot.tree.command(
    name="remove_notif",
    description="Supprime une notification YouTube ou Twitch"
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    plateforme="youtube ou twitch",
    notif_id="ID de la notification à supprimer"
)
@app_commands.choices(
        plateforme=[
            app_commands.Choice(name="YouTube", value="youtube"),
            app_commands.Choice(name="Twitch", value="twitch")
        ]
    )
async def remove_notif(
    interaction: discord.Interaction,
    plateforme: str,
    notif_id: int
):
    guild_id = interaction.guild.id
    if plateforme == "youtube":
        success = asterodb.delete_yt_notif(guild_id, notif_id)

    elif plateforme == "twitch":
        success = asterodb.delete_tw_notif(guild_id, notif_id)
    else:
        await interaction.response.send_message(
            "❌ Plateforme invalide (`Youtube` ou `Twitch`)",
            ephemeral=True
        )
        return
    if success:
        await interaction.response.send_message(
            f"✅ Notification **{plateforme}** `{notif_id}` supprimée.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"⚠️ Aucune notification **{plateforme}** trouvée avec l’ID `{notif_id}`.",
            ephemeral=True
        )

# === Gestion des réactions pour les rôles ===
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return
    message_id = payload.message_id
    emoji = str(payload.emoji)
    if message_id not in MESSAGE_EMOJIS:
        return
    if emoji not in MESSAGE_EMOJIS[message_id]:
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
    role_id = EMOJI_ROLE_MAP.get(emoji)
    if role_id is None:
        return
    role = guild.get_role(role_id)
    if role is None:
        return
    await member.add_roles(role)
    role_colors = {
        int(os.getenv("ROLE_MEMBRE")): "🟡",
        int(os.getenv("ROLE_NOTIF_TWITCH")): "🟣",
        int(os.getenv("ROLE_NOTIF_COLLEGUE")): "🔴",
        int(os.getenv("ROLE_NOTIF_PLANNING")): "🔵",
        int(os.getenv("ROLE_NOTIF_PROJETS")): "🟠",
        int(os.getenv("ROLE_NOTIF_SONDAGES")): "🔘"
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
    role_colors = {
        int(os.getenv("ROLE_MEMBRE")): "🟡",
        int(os.getenv("ROLE_NOTIF_TWITCH")): "🟣",
        int(os.getenv("ROLE_NOTIF_COLLEGUE")): "🔴",
        int(os.getenv("ROLE_NOTIF_PLANNING")): "🔵",
        int(os.getenv("ROLE_NOTIF_PROJETS")): "🟠",
        int(os.getenv("ROLE_NOTIF_SONDAGES")): "🔘"
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
    if any(var in msg for var in variantes_poire):
        await message.channel.send("Poire 🍐")
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

# == commande /droite ou gauche ==
@bot.tree.command(name="dog", description="Droite ou Gauche ?")
async def dog(interaction: discord.Interaction, msg: str):
    hash_int = int(hashlib.sha256(msg.lower().encode()).hexdigest(), 16)
    dog_result = hash_int % 100
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
    await interaction.response.defer(ephemeral=True)
    try:
        logs_channel = bot.get_channel(int(os.getenv("LOGS")))
        if nombre is not None:
            if nombre < 1:
                await interaction.followup.send("Le nombre de messages doit être supérieur à 0.", ephemeral=True)
                return
            deleted = await interaction.channel.purge(limit=nombre)
            await interaction.followup.send(f"🗑️ {len(deleted)} messages supprimés.", ephemeral=True)
            if logs_channel:
                await logs_channel.send(f"🗑️ {interaction.user.display_name} a supprimé {len(deleted)} messages dans #{interaction.channel.name}.")
        else:
            deleted = await interaction.channel.purge()
            await interaction.followup.send("🗑️ Tous les messages du salon ont été supprimés.", ephemeral=True)
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
        await interaction.response.send_message(
            "⛔ La durée doit être supérieure à 0 jour(s).",
            ephemeral=True
        )
        return
    unban_time = int((datetime.now(timezone.utc) + timedelta(days=jours)).timestamp())
    server_name = interaction.guild.name if interaction.guild else "ce serveur"
    try:
        await membre.send(
            f"Tu as été banni temporairement de {server_name} pendant {jours} jour(s)."
        )
    except Exception:
        pass
    await membre.ban(
        reason=f"Ban temporaire de {jours} jour(s) par {interaction.user.display_name}."
    )
    asterodb.save_temp_ban(
        id_serveur=interaction.guild.id,
        id_membre=membre.id,
        temps_ban=unban_time
    )
    logs_channel = bot.get_channel(int(os.getenv("LOGS")))
    if logs_channel:
        await logs_channel.send(
            f"⛔ {membre.mention} a été banni temporairement pendant {jours} jour(s)."
        )
    await interaction.response.send_message(
        f"✅ {membre.mention} a été banni temporairement pendant {jours} jour(s).",
        ephemeral=True
    )

# === Commande /help ===
@bot.tree.command(name="help", description="Affiche toutes les commandes du bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Centre d'aide d'Astero",
        description="Voici la liste des commandes disponibles avec Astero !",
        color=discord.Color.orange()
    )
    # Commandes utilisables par tous
    embed.add_field(
        name="/akkun",
        value="Affiche les chaînes Akkun7",
        inline=False
    )
    embed.add_field(
        name="/dog",
        value="Droite ou Gauche ?",
        inline=False
    )
    embed.add_field(
        name="/falnix",
        value="Affiche les chaînes Falnix",
        inline=False
    )
    embed.add_field(
        name="/saphira",
        value="Affiche le serveur de Saphira",
        inline=False
    )
    embed.add_field(
        name="/say",
        value="Faire parler le bot",
        inline=False
    )
    # Commandes administrateurs
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━",
        value="**Commandes Administrateurs**",
        inline=False
    )
    embed.add_field(
        name="/aban (Admin)",
        value="Bannir un membre",
        inline=False
    )
    embed.add_field(
        name="/add_notif (Admin)",
        value="Ajoute une notification communautaire",
        inline=False
    )
    embed.add_field(
        name="/akick (Admin)",
        value="Expulser un membre",
        inline=False
    )
    embed.add_field(
        name="/awarn (Admin)",
        value="Alerte un membre",
        inline=False
    )
    embed.add_field(
        name="/clear (Admin)",
        value="Supprime des messages dans ce salon",
        inline=False
    )
    embed.add_field(
        name="/list_notif (Admin)",
        value="Liste toutes les notifications communautaires du serveur",
        inline=False
    )
    embed.add_field(
        name="/remove_notif (Admin)",
        value="Supprime une notification communautaire",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))