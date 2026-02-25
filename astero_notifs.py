import discord
import os
from discord import app_commands
from discord.ext import commands
import feedparser
import asyncio
import aiohttp
import random
import re

import astero_db
import astero_logs

class NotifsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_youtube(self):
        await self.bot.wait_until_ready()
        while True:
            rows = astero_db.get_all_yt_notifs()
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
                if astero_db.is_yt_video_posted(channel_id, video_id):
                    continue
                for salon_id, role in targets:
                    salon = self.bot.get_channel(salon_id)
                    if not salon:
                        continue
                    if role == "everyone":
                        mention = "||@everyone||\n"
                    elif role in [None, "none"]:
                        mention = ""
                    else:
                        mention = f"||<@&{role}>||\n"
                    await salon.send(f"{mention}# {entry.title}\n{entry.link}")
                astero_db.mark_yt_video_posted(channel_id, video_id)
            await asyncio.sleep(180)

    async def check_twitch(self):
        await self.bot.wait_until_ready()
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
            rows = astero_db.get_all_tw_notifs()
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
                        salon = self.bot.get_channel(salon_id)
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
            await asyncio.sleep(60)

    @app_commands.command(name="add_notif", description="Ajoute une notification YouTube ou Twitch")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        type="Plateforme (YouTube ou Twitch)",
        salon="Salon où poster la notification",
        identifiant="ID chaîne YouTube (UC...) ou login/ID Twitch",
        role="Rôle à mentionner (@role, ID, @everyone ou 'none')"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Twitch", value="twitch")
    ])
    async def add_notif(self, interaction: discord.Interaction, type: app_commands.Choice[str], salon: discord.TextChannel, identifiant: str, role: str):
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.guild:
            await interaction.followup.send("❌ Cette commande doit être utilisée dans un serveur.")
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
                await interaction.followup.send("❌ Rôle invalide.\n\nFormats acceptés :\n• `@role`\n• `123456789`\n• `@everyone`\n• `none`")
                return

        try:
            if type.value == "youtube":
                astero_db.insert_astero_yt(id_serveur=id_serveur, id_salon=id_salon, lien_chaine=identifiant, id_role=id_role)
            else:
                astero_db.insert_astero_tw(id_serveur=id_serveur, id_salon=id_salon, id_twitch=identifiant, id_role=id_role)
            
            await interaction.followup.send(f"✅ Notification {type.name} ajoutée avec succès !")
        
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur base de données :\n```{e}```")
            return
        
        # Envoi des logs
        logs_channel = astero_logs.get_logs(self.bot, interaction.guild.id)
        if logs_channel:
            emoji_yt = "<:youtube:1475959708518187008>"
            emoji_tw = "<:twitch:1475959730051747933>"
            
            emoji = emoji_yt if type.value == "youtube" else emoji_tw
            
            role_mention = f"<@&{id_role}>" if id_role and id_role != "everyone" else ("@everyone" if id_role == "everyone" else "aucun")
            await logs_channel.send(f"{emoji} {interaction.user.mention} a ajouté une notification pour `{identifiant}` dans {salon.mention} (Mention : {role_mention}).")


    @app_commands.command(name="remove_notif", description="Supprime une notification YouTube ou Twitch")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(plateforme="youtube ou twitch", notif_id="ID de la notification à supprimer")
    @app_commands.choices(plateforme=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Twitch", value="twitch")
    ])
    async def remove_notif(self, interaction: discord.Interaction, plateforme: app_commands.Choice[str], notif_id: int):
        guild_id = interaction.guild.id
        p_val = plateforme.value 
        
        if p_val == "youtube":
            success = astero_db.delete_yt_notif(guild_id, notif_id)
        elif p_val == "twitch":
            success = astero_db.delete_tw_notif(guild_id, notif_id)
        else:
            await interaction.response.send_message("❌ Plateforme invalide", ephemeral=True)
            return

        if success:
            await interaction.response.send_message(f"✅ Notification {p_val} supprimée.", ephemeral=True)
            logs_channel = astero_logs.get_logs(self.bot, interaction.guild.id)
            if logs_channel:
                emoji = "<:youtube:1475959770371325962>" if p_val == "youtube" else "<:twitch:1475959787475697697>"
                await logs_channel.send(f"🗑️ {interaction.user.mention} a supprimé la notification {emoji} avec l'ID `{notif_id}`.")
        else:
            await interaction.response.send_message(f"⚠️ Aucune notification **{p_val}** trouvée avec l'ID `{notif_id}`.", ephemeral=True)

async def setup(bot):
    cog = NotifsCog(bot)
    await bot.add_cog(cog)
    bot.loop.create_task(cog.check_youtube())
    bot.loop.create_task(cog.check_twitch())