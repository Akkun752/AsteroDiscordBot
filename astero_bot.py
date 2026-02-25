import discord
import os
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime

import astero_db
import astero_notifs
import astero_moderation
import astero_commands
import astero_rolereacts
import astero_welcome
import astero_logs
from astero_logs import log_action, send_log

load_dotenv()

# Configuration
VERSION = "v4.2.2"
print(f"Lancement du bot Astero {VERSION}...")

# --- Configuration du dossier de Logs ---
if not os.path.exists("logs"):
    os.makedirs("logs")


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_index = 0
        # Exposé sur le bot pour rétrocompatibilité si besoin
        self.log_action = log_action

    async def setup_hook(self):
        # Chargement des modules (Cogs)
        await astero_notifs.setup(self)
        await astero_moderation.setup(self)
        await astero_commands.setup(self)
        await astero_welcome.setup(self)
        await astero_rolereacts.setup(self)
        await astero_logs.setup(self)

        # Lancement de la boucle de changement de statut
        self.change_status.start()
        await self.tree.sync()

    # --- Tâche de changement de statut (toutes les 10 secondes) ---
    @tasks.loop(seconds=10)
    async def change_status(self):
        nb_serveurs = len(self.guilds)

        statuts = [
            f"⚔️ /help | {nb_serveurs} serveurs",
            f"⚔️ /help | {VERSION}",
            "⚔️ /help | by Akkun7"
        ]

        current_status = statuts[self.status_index]

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=current_status
        )
        await self.change_presence(status=discord.Status.online, activity=activity)
        self.status_index = (self.status_index + 1) % len(statuts)

    @change_status.before_loop
    async def before_change_status(self):
        await self.wait_until_ready()


bot = MyBot(command_prefix="!", intents=discord.Intents.all())


# === Événement au démarrage ===
@bot.event
async def on_ready():
    print(f"Bot en route ! Connecté sur {len(bot.guilds)} serveurs.")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")


# === Événement quand un membre rejoint ===
@bot.event
async def on_member_join(member: discord.Member):
    # Gestion du message de Bienvenue
    welcome_channel_id = astero_db.get_welcome_channel(member.guild.id)
    if welcome_channel_id:
        welcome_channel = bot.get_channel(int(welcome_channel_id))
        if welcome_channel:
            embed = discord.Embed(
                title=f"Bienvenue {member.display_name} !",
                description="Passe un agréable moment avec nous !",
                color=discord.Color.orange()
            )
            embed.set_image(url="https://www.akkunverse.fr/astero/welcome.png")
            await welcome_channel.send(embed=embed)

    # Gestion des Logs de join (salon + fichier)
    join_msg = f"👋 {member.mention} (`{member.display_name}`) a rejoint le serveur."
    await send_log(
        bot, member.guild.id,
        message=join_msg,
        user=str(member),
        action=f"member_join → {member.display_name} ({member.id}) sur {member.guild.name}"
    )


# === Lancer le bot ===
bot.run(os.getenv("DISCORD_TOKEN"))
