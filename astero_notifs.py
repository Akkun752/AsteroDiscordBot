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
from astero_logs import send_log

class NotifsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_notif", description="Ajoute une notification YouTube ou Twitch")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
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

        emoji_yt = "<:youtube:1475959708518187008>"
        emoji_tw = "<:twitch:1475959730051747933>"
        emoji = emoji_yt if type.value == "youtube" else emoji_tw
        role_mention = f"<@&{id_role}>" if id_role and id_role != "everyone" else ("@everyone" if id_role == "everyone" else "aucun")

        discord_msg = f"{emoji} {interaction.user.mention} a ajouté une notification pour `{identifiant}` dans {salon.mention} (Mention : {role_mention})."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"add_notif {type.name} → identifiant='{identifiant}', salon=#{salon.name}, role={role_mention} sur {interaction.guild.name}"
        )

    @app_commands.command(name="remove_notif", description="Supprime une notification YouTube ou Twitch")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
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
            emoji = "<:youtube:1475959770371325962>" if p_val == "youtube" else "<:twitch:1475959787475697697>"
            discord_msg = f"🗑️ {interaction.user.mention} a supprimé la notification {emoji} avec l'ID `{notif_id}`."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg,
                user=str(interaction.user),
                action=f"remove_notif {p_val} → ID {notif_id} sur {interaction.guild.name}"
            )
        else:
            await interaction.response.send_message(f"⚠️ Aucune notification **{p_val}** trouvée avec l'ID `{notif_id}`.", ephemeral=True)

    @app_commands.command(
        name="list_notif",
        description="Liste les notifications YouTube et Twitch de ce serveur"
    )
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def list_notif(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        rows = astero_db.get_notifs_for_guild(guild_id)
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
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    cog = NotifsCog(bot)
    await bot.add_cog(cog)
