import discord
from discord import app_commands
from discord.ext import commands

import astero_db
import astero_logs
from astero_logs import send_log

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Commande /welcome_set ===
    @app_commands.command(name="welcome_set", description="Définit le salon de bienvenue de ce serveur")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(salon="Salon où envoyer les messages de bienvenue")
    async def welcome_set(self, interaction: discord.Interaction, salon: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        try:
            astero_db.set_welcome_channel(interaction.guild.id, salon.id)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur base de données :\n```{e}```", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Salon de bienvenue défini : {salon.mention}", ephemeral=True)
        discord_msg = f"👋 {interaction.user.mention} a défini {salon.mention} comme salon de bienvenue."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"welcome_set → salon #{salon.name} ({salon.id}) sur {interaction.guild.name}"
        )

    # === Commande /welcome_remove ===
    @app_commands.command(name="welcome_remove", description="Supprime le salon de bienvenue de ce serveur")
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.default_permissions(administrator=True)
    async def welcome_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        success = astero_db.remove_welcome_channel(interaction.guild.id)
        if success:
            discord_msg = f"🗑️ {interaction.user.mention} a supprimé le salon de bienvenue."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg,
                user=str(interaction.user),
                action=f"welcome_remove sur {interaction.guild.name}"
            )
            await interaction.response.send_message("✅ Salon de bienvenue supprimé.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucun salon de bienvenue configuré.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
