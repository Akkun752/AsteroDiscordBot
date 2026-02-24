import discord
import os
from discord import app_commands
from discord.ext import commands

import astero_db
import astero_logs


class RoleReactsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _normalize_emoji(self, emoji: discord.PartialEmoji) -> str:
        """Normalise l'emoji pour correspondre à ce qui est stocké en DB.
        - Emoji classique (ex: ✅) → retourne le caractère unicode
        - Emoji custom (ex: <:nom:123456>) → retourne <:nom:id>
        """
        if emoji.is_custom_emoji():
            return str(emoji)  # format : <:nom:id> ou <a:nom:id>
        return emoji.name    # caractère unicode ex: ✅

    # === Ajout de rôle au clic ===
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        emoji = self._normalize_emoji(payload.emoji)
        row = astero_db.get_role_react_by_message_and_emoji(payload.message_id, emoji)
        if not row:
            return
        id_serveur, id_role = row
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        role = guild.get_role(int(id_role))
        if not role:
            return
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print(f"❌ Impossible d'ajouter {role.name} à {member.display_name} (permissions manquantes).")
            return
        logs_channel = astero_logs.get_logs(self.bot, guild.id)
        if logs_channel:
            await logs_channel.send(f"🎭 {role.mention} ajouté à {member.mention} via réaction.")

    # === Retrait de rôle au clic ===
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji = self._normalize_emoji(payload.emoji)
        row = astero_db.get_role_react_by_message_and_emoji(payload.message_id, emoji)
        if not row:
            return
        id_serveur, id_role = row
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        role = guild.get_role(int(id_role))
        if not role:
            return
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            print(f"❌ Impossible de retirer {role.name} à {member.display_name} (permissions manquantes).")
            return
        logs_channel = astero_logs.get_logs(self.bot, guild.id)
        if logs_channel:
            await logs_channel.send(f"🎭 {role.mention} retiré à {member.mention} via réaction.")

    # === Commande /add_role_react ===
    @app_commands.command(name="add_role_react", description="Associe un emoji sur un message à un rôle")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        message_id="ID du message de réaction",
        emoji="L'emoji à utiliser. Classique: ✅  Custom: colle l'emoji depuis Discord",
        role="Le rôle à attribuer"
    )
    async def add_role_react(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
        role: discord.Role
    ):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        # Normalise l'emoji saisi : si c'est un emoji custom collé (<:nom:id>), on le garde tel quel
        emoji = emoji.strip()
        try:
            astero_db.insert_role_react(
                id_serveur=interaction.guild.id,
                id_message=message_id,
                emoji=emoji,
                id_role=role.id
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur base de données :\n```{e}```", ephemeral=True)
            return
        logs_channel = astero_logs.get_logs(self.bot, interaction.guild.id)
        if logs_channel:
            await logs_channel.send(f"⚙️ {interaction.user.mention} a lié l'emoji {emoji} au rôle {role.mention} sur le message `{message_id}`.")
        await interaction.response.send_message(
            f"✅ Role react ajouté !\n\n"
            f"• Message : `{message_id}`\n"
            f"• Emoji : {emoji}\n"
            f"• Rôle : {role.mention}",
            ephemeral=True
        )

    # === Commande /list_role_react ===
    @app_commands.command(name="list_role_react", description="Liste les role reacts de ce serveur")
    @app_commands.default_permissions(administrator=True)
    async def list_role_react(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        rows = astero_db.get_role_reacts_for_guild(interaction.guild.id)
        if not rows:
            await interaction.response.send_message(
                "📭 Aucun role react configuré sur ce serveur.", ephemeral=True
            )
            return
        blocks = []
        for react_id, id_message, emoji, id_role in rows:
            blocks.append(
                f"**#{react_id}** — {emoji} → <@&{id_role}>\n"
                f"Message : `{id_message}`"
            )
        embed = discord.Embed(
            title="🎭 Role Reacts du serveur",
            description="\n────────────\n".join(blocks),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Suppression : /remove_role_react <id>")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === Commande /remove_role_react ===
    @app_commands.command(name="remove_role_react", description="Supprime un role react de ce serveur")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(react_id="ID du role react à supprimer (visible via /list_role_react)")
    async def remove_role_react(self, interaction: discord.Interaction, react_id: int):
        if not interaction.guild:
            await interaction.response.send_message("❌ Commande réservée à un serveur.", ephemeral=True)
            return
        success = astero_db.delete_role_react(interaction.guild.id, react_id)
        if success:
            await interaction.response.send_message(
                f"✅ Role react `{react_id}` supprimé.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Aucun role react trouvé avec l'ID `{react_id}` sur ce serveur.", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RoleReactsCog(bot))