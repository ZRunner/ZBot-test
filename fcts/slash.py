import typing
from typing import Any, Callable, Coroutine

import discord
from discord.ext import commands
from libs.slash_api import SlashClient, SlashContext, SlashMember
from utils import zbot


class Slash(commands.Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "slash"
        self.global_cmds: dict[int, Callable[[SlashContext],
                                          Coroutine[Any, Any, None]]] = dict()
        self._default_cmds = {
            'ping': self.ping,
            'add-tag': self.add_tag,
            'remove-tag': self.remove_tag,
            'about-tags': self.tag_info
        }

    @commands.Cog.listener()
    async def on_ready(self):
        self.client = SlashClient(self.bot)
        await self.sync_cmds()

    @commands.Cog.listener()
    async def on_socket_response(self, msg: dict):
        if msg['t'] != "INTERACTION_CREATE":
            return
        try:
            cmd_id: int = int(msg['d']['data']['id'])
            fct = self.global_cmds.get(cmd_id, self.custom_tag)
            ctx = SlashContext(msg['d'], self.client)
            if 'options' in msg['d']['data']:
                args: list[Any] = [await self.parse_argument(a) for a in msg['d']['data']['options']]
            else:
                args = list()
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e)
            return
        try:
            await fct(ctx, *args)
        except Exception as e:
            await self.on_slash_command_error(ctx, e)

    async def parse_argument(self, arg: dict[str, str]) -> Any:
        if arg['type'] == 3:
            return arg['value']
        return arg['value']

    async def sync_cmds(self):
        """Get slash commands from Discord API to properly catch them here"""
        # save global commands
        cmds: list[dict] = await self.client.get_all_commands()
        for cmd in cmds:
            cmd_id: int = int(cmd['id'])
            if cmd_id not in self.global_cmds and cmd['name'] in self._default_cmds:
                self.bot.log.info(
                    f"Loading global slash command {cmd['name']}")
                self.global_cmds[cmd_id] = self._default_cmds[cmd['name']]

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, err: Exception):
        self.bot.log.error("[on_slash_command] New error:", exc_info=err)

    async def is_allowed(self, author: SlashMember) -> bool:
        """Check if a discord User is allowed to use /add-tag or /remove-tag"""
        return bool(author.permissions.manage_guild)

    async def ping(self, ctx: SlashContext):
        """Give the websocket latency to the user"""
        await ctx.send(content=f"Pong! (`{round(self.bot.latency*1000)}`ms)")

    async def add_tag(self, ctx: SlashContext, name: str, answer: str):
        """Add a new custom tag in a guild"""
        if ctx.guild_id is None or not isinstance(ctx.author, SlashMember):
            await ctx.send(await self.bot._(ctx.author.id, "errors", "DM"))
            return
        if not await self.is_allowed(ctx.author):
            await ctx.send(await self.bot._(ctx.guild_id, "server", "need-manage-server"))
            return
        if len(name.split()) > 1:
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "only-one-word"))
            return
        check_exists = await self.db_get_command(ctx.guild_id, name)
        if check_exists is not None:
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "already-exists"))
            return
        check_discord_exists = await self.disc_get_command(ctx.guild_id, name)
        desc = "something"
        try:
            cmd = await self.client.add_command(ctx.guild_id, name, desc)
        except Exception as e:
            self.bot.log.debug(f"{type(e)} {e}")
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "already-exists"))
            return
        await self.db_add_command(cmd['id'], ctx.guild_id, name, desc, answer)
        await ctx.send(await self.bot._(ctx.guild_id, "slash", "command-created", name=name, answer=answer))

    async def remove_tag(self, ctx: SlashContext, name: str):
        """Remove a custom tag from a guild"""
        if ctx.guild_id is None or not isinstance(ctx.author, SlashMember):
            await ctx.send(await self.bot._(ctx.author.id, "errors", "DM"))
            return
        if not await self.is_allowed(ctx.author):
            await ctx.send(await self.bot._(ctx.guild_id, "server", "need-manage-server"))
            return
        if len(name.split()) > 1:
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "only-one-word"))
            return
        cmd_id = None
        check_exists = await self.db_get_command(ctx.guild_id, name)
        if check_exists is None:
            check_discord_exists = await self.disc_get_command(ctx.guild_id, name)
            if check_discord_exists is None:
                await ctx.send(await self.bot._(ctx.guild_id, "slash", "command-not-found"))
                return
            cmd_id = check_discord_exists['id']
        else:
            cmd_id = check_exists['ID']
        if await self.disc_delete_command(ctx.guild_id, cmd_id):
            if check_exists:  # if it doesn't exist in our database, we don't need to delete it there
                await self.db_delete_command(ctx.guild_id, cmd_id)
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "command-deleted", name=name))
        else:
            await ctx.send(await self.bot._(ctx.guild_id, "slash", "deletion-failed"))

    async def tag_info(self, ctx: SlashContext):
        """Get info about the tags system"""
        botinvite = "<" + discord.utils.oauth_url(self.bot.user.id, scopes=['bot', 'applications.commands']) + ">"
        slashinvite = "<" + discord.utils.oauth_url(self.bot.user.id, scopes=['applications.commands']) + ">"
        ID = ctx.guild_id or ctx.author.id
        await ctx.send(await self.bot._(ID, "slash", "about", slashinvite=slashinvite, botinvite=botinvite))

    async def custom_tag(self, ctx: SlashContext, *args, **kwargs):
        """Executes a custom command"""
        answ = await self.db_get_command_id(int(ctx.command.id))
        if answ is None:
            return
        await ctx.send(answ['answer'])

    async def db_get_commands(self, guildid: int) -> list[dict]:
        """Get the guild commands from the database"""
        cursor = self.bot.cnx_frm.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM slash_commands WHERE guild=?", (guildid,))
        res = list(cursor)
        cursor.close()
        return res

    async def db_get_command(self, guildid: int, name: str) -> typing.Optional[dict]:
        """Get a command from its name and guild"""
        cursor = self.bot.cnx_frm.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM slash_commands WHERE guild=%s AND name=%s", (guildid, name))
        res = list(cursor)
        cursor.close()
        if len(res) == 0:
            return None
        return res[0]

    async def db_get_command_id(self, ID: int) -> typing.Optional[dict]:
        """Get a command from its ID"""
        cursor = self.bot.cnx_frm.cursor(dictionary=True)
        cursor.execute("SELECT * FROM slash_commands WHERE ID = %s", (ID,))
        res = list(cursor)
        cursor.close()
        if len(res) == 0:
            return None
        return res[0]

    async def db_add_command(self, ID: int, guildid: int, name: str, description: str, answer: str):
        """Add a slash command into the database"""
        cursor = self.bot.cnx_frm.cursor()
        cursor.execute("INSERT INTO slash_commands (`ID`, `guild`, `name`, `description`, `answer`) VALUES (%s, %s, %s, %s, %s)",
                       (ID, guildid, name, description, answer))
        self.bot.cnx_frm.commit()
        cursor.close()

    async def db_delete_command(self, guildid: int, ID: int):
        """Delete a slash command from the database"""
        cursor = self.bot.cnx_frm.cursor()
        cursor.execute(
            "DELETE FROM slash_commands WHERE ID = %s AND guild = %s", (ID, guildid))
        self.bot.cnx_frm.commit()
        cursor.close()

    async def disc_delete_command(self, guildid: int, ID: int):
        """Remove a slash command from Discord API"""
        r = await self.client.remove_command(guildid, ID)
        if not 200 <= r <= 204:
            self.bot.log.warn(f"[slash_command] Something went wrong when deleting custom command {ID}: Discord answered {r}")
            return False
        self.global_cmds.pop(ID, None)
        return True

    async def disc_get_command(self, guildid: int, name: str) -> typing.Optional[dict]:
        """Get a slash command from Discord API"""
        g_cmds: list[dict] = await self.client.get_all_commands(guildid)
        result = [x for x in g_cmds if x['name'] == name]
        return result[0] if result else None


def setup(bot):
    bot.add_cog(Slash(bot))
