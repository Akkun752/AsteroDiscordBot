import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import os

import astero_db


# ============================================================
# === Utilitaire de log fichier + console ====================
# ============================================================

def log_action(user: str, action: str):
    """Enregistre une action dans la console et dans un fichier log quotidien."""
    timestamp = datetime.now().strftime("%Y-%m-%d : %H:%M:%S")
    log_message = f"[{timestamp}] {user} a fait : {action}"

    # Affichage console
    print(log_message)

    # Écriture fichier (un fichier par jour)
    if not os.path.exists("logs"):
        os.makedirs("logs")
    file_name = f"logs/log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(file_name, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


# ============================================================
# === Helper salon de logs ===================================
# ============================================================

def get_logs(bot, guild_id) -> discord.TextChannel | None:
    """Helper global : retourne le salon de logs du serveur, ou None."""
    salon_id = astero_db.get_logs_channel(guild_id)
    if not salon_id:
        return None
    return bot.get_channel(int(salon_id))


async def send_log(bot, guild_id: int, message: str, user: str = None, action: str = None):
    """Envoie un log dans le salon Discord ET dans le fichier/console.

    - message : texte à envoyer dans le salon Discord
    - user    : label pour le log fichier (ex: "Akkun7#1234"), si None → pas de log fichier
    - action  : description pour le log fichier, si None → utilise `message` brut
    """
    # Log salon Discord
    logs_channel = get_logs(bot, guild_id)
    if logs_channel:
        await logs_channel.send(message)

    # Log fichier + console
    if user is not None:
        log_action(user, action if action is not None else message)


# ============================================================
# === Cog LogsCog ============================================
# ============================================================

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

        discord_msg = f"⚙️ {interaction.user.mention} a défini {salon.mention} comme salon de logs."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"logs_set → salon #{salon.name} ({salon.id}) sur serveur {interaction.guild.name}"
        )
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
            # On log AVANT de perdre la référence au salon
            discord_msg = f"🗑️ {interaction.user.mention} a supprimé le salon de logs."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg,
                user=str(interaction.user),
                action=f"logs_remove sur serveur {interaction.guild.name}"
            )
            await interaction.response.send_message("✅ Salon de logs supprimé.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucun salon de logs configuré sur ce serveur.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(LogsCog(bot))
