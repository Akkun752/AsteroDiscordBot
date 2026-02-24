import discord
from discord import app_commands
from discord.ext import commands


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Commande /help ===
    @app_commands.command(name="help", description="Affiche toutes les commandes du bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Centre d'aide d'Astero",
            description="Voici la liste des commandes disponibles avec Astero !",
            color=discord.Color.orange()
        )
        # --- Commandes Utilisateurs ---
        embed.add_field(name="/akkun", value="Affiche les chaînes Akkun7", inline=False)
        embed.add_field(name="/falnix", value="Affiche les chaînes Falnix", inline=False)
        embed.add_field(name="/saphira", value="Affiche le serveur de Saphira", inline=False)
        embed.add_field(name="/say", value="Faire parler le bot", inline=False)

        # --- Séparateur ---
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="**Commandes Administrateurs**", inline=False)

        # --- Commandes Administrateurs (Ordre Alphabétique) ---
        embed.add_field(name="/aban (Admin)", value="Bannir un membre", inline=False)
        embed.add_field(name="/add_notif (Admin)", value="Ajoute une notification communautaire", inline=False)
        embed.add_field(name="/add_role_react (Admin)", value="Ajoute un rôle réaction", inline=False)
        embed.add_field(name="/akick (Admin)", value="Expulser un membre", inline=False)
        embed.add_field(name="/awarn (Admin)", value="Alerte un membre", inline=False)
        embed.add_field(name="/clear (Admin)", value="Supprime des messages dans ce salon", inline=False)
        embed.add_field(name="/filter_add (Admin)", value="Ajoute un filtre de texte sur un salon", inline=False)
        embed.add_field(name="/filter_list (Admin)", value="Liste les filtres de texte du serveur", inline=False)
        embed.add_field(name="/filter_remove (Admin)", value="Supprime un filtre de texte", inline=False)
        embed.add_field(name="/list_notif (Admin)", value="Liste toutes les notifications communautaires", inline=False)
        embed.add_field(name="/list_role_react (Admin)", value="Liste tous les rôles réactions du serveur", inline=False)
        embed.add_field(name="/logs_remove (Admin)", value="Supprime le salon de logs du serveur", inline=False)
        embed.add_field(name="/logs_set (Admin)", value="Définit le salon de logs du serveur", inline=False)
        embed.add_field(name="/remove_notif (Admin)", value="Supprime une notification communautaire", inline=False)
        embed.add_field(name="/remove_role_react (Admin)", value="Supprime un rôle réaction", inline=False)
        embed.add_field(name="/welcome_remove (Admin)", value="Supprime le salon de bienvenue du serveur", inline=False)
        embed.add_field(name="/welcome_set (Admin)", value="Définit le salon de bienvenue du serveur", inline=False)
        await interaction.response.send_message(embed=embed)

    # === Commande /embed ===
    @app_commands.command(name="embed", description="Créer un Embed")
    @app_commands.default_permissions(administrator=True)
    async def embed_cmd(self, interaction: discord.Interaction, titre: str, desc: str, soustitre: str, contenu: str):
        embed = discord.Embed(title=titre, description=desc, color=discord.Color.orange())
        embed.add_field(name=soustitre, value=contenu)
        await interaction.response.send_message(embed=embed)

    # === Commande /say ===
    @app_commands.command(name="say", description="Faire parler le bot")
    async def say(self, interaction: discord.Interaction, msg: str):
        await interaction.response.send_message(msg)

    # === Commande /akkun ===
    @app_commands.command(name="akkun", description="Affiche les chaînes Akkun7")
    async def akkun(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Les chaînes de Akkun :**\n"
            "🎥 YouTube : https://youtube.com/@Akkun7\n"
            "🎬 YouTube VOD : https://youtube.com/@Akkun7VOD\n"
            "👾 Twitch : https://twitch.tv/akkun752"
        )

    # === Commande /falnix ===
    @app_commands.command(name="falnix", description="Affiche les chaînes Falnix")
    async def falnix(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Les chaînes de Falnix :**\n"
            "🎥 YouTube : https://youtube.com/@Falnix\n"
            "👾 Twitch : https://twitch.tv/falnix_"
        )

    # === Commande /saphira ===
    @app_commands.command(name="saphira", description="Affiche le serveur de Saphira")
    async def saphira(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Les différents liens de Saphira :**\n"
            "🤖​ Discord : https://discord.gg/xmkZcekE8J\n"
            "🌐​ Site web : https://saphira-bump.fr"
        )

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
