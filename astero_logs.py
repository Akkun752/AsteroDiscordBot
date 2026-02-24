import discord
from discord import app_commands
from discord.ext import commands

import astero_db


def get_logs(bot, guild_id) -> discord.TextChannel | None:
    """Helper global : retourne le salon de logs du serveur, ou None."""
    salon_id = astero_db.get_logs_channel(guild_id)
    if not salon_id:
        return None
    return bot.get_channel(int(salon_id))


class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Commande /logs_set ===
    @app_commands.command(name="logs_set", description="Définit le salon de logs de ce serveur")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(salon="Salon où envoyer les logs")
    async def logs_set(self, interaction: discord.Interaction, salon: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        try:
            astero_db.set_logs_channel(interaction.guild.id, salon.id)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur base de données :\n```{e}```", ephemeral=True)
            return
        logs_channel = get_logs(self.bot, interaction.guild.id)
        if logs_channel:
            await logs_channel.send(f"⚙️ {interaction.user.mention} a défini {salon.mention} comme salon de logs.")
        await interaction.response.send_message(
            f"✅ Salon de logs défini : {salon.mention}", ephemeral=True
        )

    # === Commande /logs_remove ===
    @app_commands.command(name="logs_remove", description="Supprime le salon de logs de ce serveur")
    @app_commands.default_permissions(administrator=True)
    async def logs_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        success = astero_db.remove_logs_channel(interaction.guild.id)
        if success:
            logs_channel = get_logs(self.bot, interaction.guild.id)
            if logs_channel:
                await logs_channel.send(f"🗑️ {interaction.user.mention} a supprimé le salon de logs.")
            await interaction.response.send_message("✅ Salon de logs supprimé.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucun salon de logs configuré sur ce serveur.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LogsCog(bot))
