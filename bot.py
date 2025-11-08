import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
load_dotenv()

print("Lancement du bot...")
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

welcome_channel = bot.get_channel(1227635256492949604)
logs_channel = bot.get_channel(1435730840691937301)
youtube_channel = bot.get_channel(1226934231259676834)
twitch_channel = bot.get_channel(1435706879077781706)

@bot.event
async def on_ready():

    print("Bot en route !")

    #synchroniser les commandes
    try:
        #sync
        synchronised = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synchronised)}")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    if (message.content.lower() == "asterion" or message.content.lower() == "astérion"):
        channel=message.channel
        author=message.author
        await channel.send(f"{author}, tu ne peut pas dire ça.")

@bot.tree.command(name="youtube", description="Affiche la chaîne Akkun7")
async def youtube(interaction: discord.Integration):
    await interaction.response.send_message("Voici la chaîne Akkun7 : https://youtube.com/@Akkun7")

@bot.tree.command(name="warn", description="Alerte un membre")
async def warn(interaction: discord.Integration, member: discord.Member):
    logs_channel = bot.get_channel(1435730840691937301)
    await logs_channel.send(f"{member} a reçu une alerte.")
    await interaction.response.send_message(f"{member} a reçu une alerte.")
    await member.send("Tu as reçu une alerte.")

@bot.tree.command(name="ban", description="Bannir un membre")
async def ban(interaction: discord.Integration, member: discord.Member):
    logs_channel = bot.get_channel(1435730840691937301)
    await logs_channel.send(f"{member} a été banni.")
    await member.send("Tu as été banni.")
    await member.ban(reason="Un modérateur a banni cet utilisateur.")
    await interaction.response.send_message(f"{member} a été banni.")

@bot.tree.command(name="kick", description="Expulser un membre")
async def kick(interaction: discord.Integration, member: discord.Member):
    logs_channel = bot.get_channel(1435730840691937301)
    await logs_channel.send(f"{member} a été expulsé.")
    await member.send("Tu as été expulsé.")
    await member.kick(reason="Un modérateur a expulé cet utilisateur.")
    await interaction.response.send_message(f"{member} a été expulsé.")

@bot.tree.command(name="embed", description="Créer un Embed")
async def embed(interaction: discord.Integration, titre: str, desc: str, soustitre: str, contenu: str):
    embed = discord.Embed(
        title=titre,
        description=desc,
        color=discord.Color.orange()
    )
    embed.add_field(name=soustitre, value=contenu)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="say", description="Dire quelque chose")
async def say(interaction: discord.Integration, msg: str):
    await interaction.response.send_message(msg)

@bot.event
async def on_member_join(member: discord.Intents.members):
    welcome_channel = bot.get_channel(1227635256492949604)
    logs_channel = bot.get_channel(1435730840691937301)
    await logs_channel.send(f"{member} a rejoint le serveur.")
    
    embed = discord.Embed(
        title=f"Bienvenue {member} !",
        description=f"{member} a rejoint le serveur !",
        color=discord.Color.orange()
    )

    await logs_channel.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))