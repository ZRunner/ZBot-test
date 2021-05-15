import typing
from typing import Any, Callable, Coroutine

from discord.ext import commands
from libs.slash_api import SlashClient, SlashContext
from utils import zbot


class Slash(commands.Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "slash"
        self.client = SlashClient(bot)
        self.commands: dict[int, Callable[[SlashContext],
                                          Coroutine[Any, Any, None]]] = dict()
        self._default_cmds = {
            'ping': self.ping,
            'add-tag': self.add_tag,
            'remove-tag': self.remove_tag
        }

    @commands.Cog.listener()
    async def on_ready(self):
        await self.sync_cmds()

    @commands.Cog.listener()
    async def on_socket_response(self, msg: dict):
        if msg['t'] != "INTERACTION_CREATE":
            return
        cmd_id: int = int(msg['d']['data']['id'])
        if cmd_id not in self.commands:
            return
        ctx = SlashContext(msg['d'], self.client)
        try:
            await self.commands[cmd_id](ctx)
        except Exception as e:
            await self.on_slash_command_error(ctx, e)

    async def sync_cmds(self):
        """Get slash commands from Discord API to properly catch them here"""
        # save global commands
        cmds: list[dict] = await self.client.get_all_commands()
        for cmd in cmds:
            if cmd['id'] not in self.commands and cmd['name'] in self._default_cmds:
                self.bot.log.info(
                    f"Loading global slash command {cmd['name']}")
                self.commands[cmd['id']] = self._default_cmds[cmd['name']]
        # save local commands
        for g in self.bot.guilds:
            g_cmds: list[dict] = await self.client.get_all_commands(g.id)
            loaded: list[str] = []
            for cmd in g_cmds:
                if cmd['id'] in self.commands:
                    continue
                self.commands[cmd['id']] = self.custom_tag
                loaded.append(cmd['name'])
            if len(loaded) > 0:
                self.bot.log.info(
                    f"Loaded local slash commands {' '.join(loaded)} for guild {g.id}")

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, err: Exception):
        self.bot.log.error("[on_slash_command] New error:", exc_info=err)

    async def ping(self, ctx: SlashContext):
        await ctx.send(content=f"Pong! (`{round(self.bot.latency*1000)}`ms)")

    async def add_tag(self, ctx: SlashContext, name: str, answer: str):
        if ctx.guild_id is None:
            await ctx.send("Cette commande n'est pas disponible en MP !")
            return
        if len(name.split()) > 1:
            await ctx.send("Le nom ne peut contenir qu'un seul mot !")
            return
        check_exists = await self.db_get_command(ctx.guild_id, name)
        if check_exists is not None:
            await ctx.send("Une commande existe déjà avec ce nom !")
            return
        check_discord_exists = await self.disc_get_command(ctx.guild_id, name)
        print(check_discord_exists)
        desc = "something"
        try:
            cmd = await self.client.add_command(ctx.guild_id, name, desc)
        except Exception as e:
            print(type(e), e)
            await ctx.send("Une commande existe déjà avec ce nom !")
            return
        await self.db_add_command(cmd['id'], ctx.guild_id, name, desc, answer)
        await ctx.send(f"La commande `/{name}` a bien été ajouté avec la réponse suivante :\n{answer}")

    async def remove_tag(self, ctx: SlashContext, name: str):
        if ctx.guild_id is None:
            await ctx.send("Cette commande n'est pas disponible en MP !")
            return
        if len(name.split()) > 1:
            await ctx.send("Le nom ne peut contenir qu'un seul mot !")
            return
        cmd_id = None
        check_exists = await self.db_get_command(ctx.guild_id, name)
        if check_exists is None:
            check_discord_exists = await self.disc_get_command(ctx.guild_id, name)
            if check_discord_exists is None:
                await ctx.send("Aucune commande n'existe avec ce nom !")
                return
            cmd_id = check_discord_exists['id']
        else:
            cmd_id = check_exists['ID']
        if await self.disc_delete_command(ctx.guild_id, cmd_id):
            if check_exists:  # if it doesn't exist in our database, we don't need to delete it there
                await self.db_delete_command(ctx.guild_id, cmd_id)
            await ctx.send(f"La commande `/{name}` a bien été supprimée !")
        else:
            await ctx.send("Oups, quelque chose s'est mal passé lors de la suppression !")

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
        self.commands.pop(ID, None)
        return True

    async def disc_get_command(self, guildid: int, name: str) -> typing.Optional[dict]:
        """Get a slash command from Discord API"""
        g_cmds: list[dict] = await self.client.get_all_commands(guildid)
        result = [x for x in g_cmds if x['name'] == name]
        return result[0] if result else None


def setup(bot):
    bot.add_cog(Slash(bot))
