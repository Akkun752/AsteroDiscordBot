import discord
import os
import asyncio
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import astero_db
from astero_logs import get_logs, send_log

mots_interdits = [
    "abruti", "fdp", "pute", "salope", "batard", "ntm", "enculé", "connard",
    "connards", "putes", "salopes", "batards", "nsm", "nique", "niquer",
    "abrutis", "enculés", "niquez", "niques"
]

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Filtre de messages (Mots interdits + Filtre de salon) ===
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        msg_lower = message.content.lower()

        # --- 1. FILTRE DE MOTS INTERDITS ---
        mots_message = msg_lower.split()
        if any(mot in mots_interdits for mot in mots_message):
            try:
                await message.delete()
                await message.channel.send(
                    f"🚫 {message.author.display_name}, tu ne peux pas dire ça ici.",
                    delete_after=5
                )
                embed = discord.Embed(
                    title="Mot interdit détecté",
                    description=f"**Utilisateur:** {message.author.mention}\n**Salon:** {message.channel.mention}\n**Message:** {message.content}",
                    color=discord.Color.red()
                )
                logs_channel = get_logs(self.bot, message.guild.id)
                if logs_channel:
                    await logs_channel.send(embed=embed)
                from astero_logs import log_action
                log_action(
                    str(message.author),
                    f"Mot interdit dans #{message.channel.name} sur {message.guild.name} : {message.content}"
                )
            except discord.Forbidden:
                pass
            return

        # --- 2. FILTRE DE CONTENU OBLIGATOIRE (Système de Filtres) ---
        required_text = astero_db.get_filter_for_channel(message.channel.id)
        if required_text:
            if required_text.lower() not in msg_lower:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass

    # === Commandes de Gestion des Filtres ===
    @app_commands.command(name="filter_add", description="Force un texte obligatoire dans un salon")
    @app_commands.default_permissions(administrator=True)
    async def filter_add(self, interaction: discord.Interaction, salon: discord.TextChannel, texte: str):
        astero_db.add_channel_filter(interaction.guild.id, salon.id, texte)
        discord_msg = f"🔧 {interaction.user.mention} a ajouté un filtre sur {salon.mention} : `{texte}`."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"filter_add → #{salon.name} ({salon.id}) filtre='{texte}' sur {interaction.guild.name}"
        )
        await interaction.response.send_message(
            f"✅ Filtre configuré : les messages dans {salon.mention} devront contenir `{texte}`.",
            ephemeral=True
        )

    @app_commands.command(name="filter_list", description="Liste les filtres de salon actifs")
    @app_commands.default_permissions(administrator=True)
    async def filter_list(self, interaction: discord.Interaction):
        rows = astero_db.get_filters(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("Aucun filtre n'est configuré sur ce serveur.", ephemeral=True)

        txt = "**Filtres de salon actifs :**\n"
        for fid, sid, texte in rows:
            txt += f"ID: `{fid}` | <#{sid}> -> `{texte}`\n"
        await interaction.response.send_message(txt, ephemeral=True)

    @app_commands.command(name="filter_remove", description="Supprime un filtre de salon via son ID")
    @app_commands.default_permissions(administrator=True)
    async def filter_remove(self, interaction: discord.Interaction, filter_id: int):
        if astero_db.delete_filter(interaction.guild.id, filter_id):
            discord_msg = f"🗑️ {interaction.user.mention} a supprimé le filtre ID `{filter_id}`."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg,
                user=str(interaction.user),
                action=f"filter_remove → ID {filter_id} sur {interaction.guild.name}"
            )
            await interaction.response.send_message(f"✅ Filtre `{filter_id}` supprimé avec succès.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ ID de filtre introuvable.", ephemeral=True)

    # === Commande /clear ===
    @app_commands.command(name="clear", description="Supprime des messages dans ce salon")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(nombre="Nombre de messages à supprimer (laisser vide pour tout supprimer)")
    async def clear(self, interaction: discord.Interaction, nombre: int = None):
        if not interaction.channel: return
        await interaction.response.defer(ephemeral=True)
        try:
            if nombre is not None:
                if nombre < 1:
                    await interaction.followup.send("Le nombre doit être > 0.", ephemeral=True)
                    return
                deleted = await interaction.channel.purge(limit=nombre)
                reply = f"🗑️ {len(deleted)} messages supprimés."
            else:
                deleted = await interaction.channel.purge()
                reply = "🗑️ Salon purgé."

            await interaction.followup.send(reply, ephemeral=True)
            discord_msg = f"🗑️ **Clear** : {interaction.user.mention} a supprimé {len(deleted)} message(s) dans {interaction.channel.mention}."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg,
                user=str(interaction.user),
                action=f"clear → {len(deleted)} messages dans #{interaction.channel.name} sur {interaction.guild.name}"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur : {e}", ephemeral=True)

    # === Commande /atban (Ban Temporaire) ===
    @app_commands.command(name="atban", description="Bannir un membre temporairement")
    @app_commands.default_permissions(administrator=True)
    async def atban(self, interaction: discord.Interaction, membre: discord.Member, jours: int):
        if jours <= 0:
            await interaction.response.send_message("⛔ Durée invalide.", ephemeral=True)
            return
        unban_time = int((datetime.now(timezone.utc) + timedelta(days=jours)).timestamp())
        try: await membre.send(f"Tu as été banni de {interaction.guild.name} pour {jours} jours.")
        except: pass

        await membre.ban(reason=f"Ban temporaire ({jours}j) par {interaction.user.display_name}")
        astero_db.save_temp_ban(interaction.guild.id, membre.id, unban_time)

        discord_msg = f"⛔ {membre.mention} banni temporairement ({jours}j) par {interaction.user.mention}."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"atban → {membre} ({membre.id}) pour {jours}j sur {interaction.guild.name}"
        )
        await interaction.response.send_message(f"✅ {membre.mention} banni pour {jours} jours.", ephemeral=True)

    # === Commande /awarn (Alerte) ===
    @app_commands.command(name="awarn", description="Alerte un membre")
    @app_commands.default_permissions(administrator=True)
    async def awarn(self, interaction: discord.Interaction, member: discord.Member):
        astero_db.add_warn(member.id)
        total_warns = astero_db.count_warns(member.id)

        try: await member.send(f"⚠️ Alerte sur **{interaction.guild.name}** ({total_warns}/4)")
        except: pass

        discord_msg = f"⚠️ {member.mention} a reçu une alerte ({total_warns}/4) de {interaction.user.mention}."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"awarn → {member} ({member.id}) warn {total_warns}/4 sur {interaction.guild.name}"
        )
        await interaction.response.send_message(f"✅ Alerte donnée à {member.mention}.", ephemeral=True)

        if total_warns >= 4:
            await member.ban(reason="4 alertes atteintes")
            astero_db.add_to_bans(member.id, raison="Ban automatique (4 warns)")
            discord_msg2 = f"⛔ {member.mention} banni automatiquement (seuil de 4 alertes atteint)."
            await send_log(
                self.bot, interaction.guild.id,
                message=discord_msg2,
                user="Système",
                action=f"auto-ban → {member} ({member.id}) sur {interaction.guild.name} (4 warns)"
            )

    # === Commande /aban (Ban Définitif) ===
    @app_commands.command(name="aban", description="Bannir un membre")
    @app_commands.default_permissions(administrator=True)
    async def aban(self, interaction: discord.Interaction, member: discord.Member):
        try: await member.send(f"Tu as été banni de {interaction.guild.name}.")
        except: pass
        await member.ban(reason=f"Banni par {interaction.user.display_name}")
        astero_db.add_to_bans(member.id, raison="Banni par modérateur")

        discord_msg = f"⛔ {member.mention} banni définitivement par {interaction.user.mention}."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"aban → {member} ({member.id}) sur {interaction.guild.name}"
        )
        await interaction.response.send_message(f"✅ {member.mention} banni.", ephemeral=True)

    # === Commande /akick (Expulsion) ===
    @app_commands.command(name="akick", description="Expulser un membre")
    @app_commands.default_permissions(administrator=True)
    async def akick(self, interaction: discord.Interaction, member: discord.Member):
        try: await member.send(f"Tu as été expulsé de {interaction.guild.name}.")
        except: pass
        await member.kick(reason=f"Expulsé par {interaction.user.display_name}")

        discord_msg = f"🚪 {member.mention} expulsé par {interaction.user.mention}."
        await send_log(
            self.bot, interaction.guild.id,
            message=discord_msg,
            user=str(interaction.user),
            action=f"akick → {member} ({member.id}) sur {interaction.guild.name}"
        )
        await interaction.response.send_message(f"✅ {member.mention} expulsé.", ephemeral=True)

    # === Tâche de fond : Bans Globaux ===
    async def check_global_bans(self):
        await self.bot.wait_until_ready()
        while True:
            bans = astero_db.get_all_bans()
            for guild in self.bot.guilds:
                for ban_entry in bans:
                    member_id = int(ban_entry["id_membre"])
                    member = guild.get_member(member_id)
                    if member:
                        try:
                            await member.ban(reason="Ban global détecté")
                        except:
                            pass
            await asyncio.sleep(300)

async def setup(bot):
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
    bot.loop.create_task(cog.check_global_bans())
