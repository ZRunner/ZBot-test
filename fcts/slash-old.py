import typing
import discord
from discord.ext import commands
from discord_slash import cog_ext
import discord_slash
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import get_all_commands, add_slash_command, remove_slash_command

from utils import zbot


class Slash(commands.Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "slash"
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.sync_cmds()
    
    def cog_unload(self):
        """Disable slash commands when cog is unloaded"""
        self.bot.slashClient.commands.clear()

    async def sync_cmds(self):
        """Get remaining slash commands from Discord API to properly catch them here"""
        # save global commands
        cmds: list[dict] = await get_all_commands(self.bot.user.id, self.bot.http.token)
        for cmd in cmds:
            if cmd['name'] not in self.bot.slashClient.commands:
                self.bot.log.info(f"Loading global slash command {cmd['name']}")
                self.bot.slashClient.add_slash_command(self.test, cmd['name'], cmd['description'])
        # save local commands
        cmds: dict[str,list[int]] = dict()
        for g in self.bot.guilds:
            g_cmds: list[dict] = await get_all_commands(self.bot.user.id, self.bot.http.token, guild_id=g.id)
            for cmd in g_cmds:
                if cmd['name'] in self.bot.slashClient.commands:
                    continue
                if cmd['name'] in cmds:
                    cmds[cmd['name']].append(g.id)
                else:
                    cmds[cmd['name']] = [g.id]
        for name, gIDs in cmds.items():
            self.bot.log.info(f"Loading local slash command {cmd['name']} for guilds {gIDs}")
            self.bot.slashClient.add_slash_command(self.test, name, guild_ids=gIDs)

    
    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, err: Exception):
        self.bot.log.error("[on_slash_command] New error:", exc_info=err)
    
    @cog_ext.cog_slash(name="ping")
    async def _slash(self, ctx: SlashContext): # Normal usage.
        await ctx.send(content=f"Pong! (`{round(self.bot.latency*1000)}`ms)")
    
    @cog_ext.cog_slash(name="add-tag")
    async def add_tag(self, ctx: SlashContext, name: str, answer: str):
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
            ID = await self.disc_add_command(ctx.guild_id, name, desc)
        except discord_slash.error.DuplicateCommand as e:
            print(e)
            await ctx.send("Une commande existe déjà avec ce nom !")
            return
        await self.db_add_command(ID, ctx.guild_id, name, desc, answer)
        await ctx.send(f"La commande `/{name}` a bien été ajouté avec la réponse suivante :\n{answer}")
    
    @cog_ext.cog_slash(name="remove-tag")
    async def remove_tag(self, ctx: SlashContext, name: str):
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
            if check_exists: # if it doesn't exist in our database, we don't need to delete it there
                await self.db_delete_command(ctx.guild_id, cmd_id)
            await ctx.send(f"La commande `/{name}` a bien été supprimée !")
        else:
            await ctx.send("Oups, quelque chose s'est mal passé lors de la suppression !")
    
    async def test(self, ctx: SlashContext, *args, **kwargs):
        """Executes a custom command"""
        answ = await self.db_get_command_id(int(ctx.command_id))
        if answ is None:
            return
        await ctx.send(answ['answer'])

    async def db_get_commands(self, guildid: int) -> list[dict]:
        """Get the guild commands from the database"""
        cursor = self.bot.cnx_frm.cursor(dictionary=True)
        cursor.execute("SELECT * FROM slash_commands WHERE guild=?", (guildid,))
        res = list(cursor)
        cursor.close()
        return res
    
    async def db_get_command(self, guildid: int, name: str) -> dict:
        """Get a command from its name and guild"""
        cursor = self.bot.cnx_frm.cursor(dictionary=True)
        cursor.execute("SELECT * FROM slash_commands WHERE guild=%s AND name=%s", (guildid, name))
        res = list(cursor)
        cursor.close()
        if len(res) == 0:
            return None
        return res[0]
    
    async def db_get_command_id(self, ID: int) -> dict:
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
        cursor.execute("INSERT INTO slash_commands (`ID`, `guild`, `name`, `description`, `answer`) VALUES (%s, %s, %s, %s, %s)", (ID, guildid, name, description, answer))
        self.bot.cnx_frm.commit()
        cursor.close()
    
    async def db_delete_command(self, guildid: int, ID: int):
        """Delete a slash command from the database"""
        cursor = self.bot.cnx_frm.cursor()
        cursor.execute("DELETE FROM slash_commands WHERE ID = %s AND guild = %s", (ID, guildid))
        self.bot.cnx_frm.commit()
        cursor.close()
    
    async def disc_add_command(self, guildid: int, name: str, description: str) -> int:
        """Add a slash command into Discord API
        
        Returns the command ID"""
        r = await add_slash_command(self.bot.user.id, self.bot.http.token, guildid, name, description)
        self.bot.slashClient.add_slash_command(self.test, name, description, guild_ids=[guildid])
        return int(r['id'])

    async def disc_delete_command(self, guildid: int, ID: int):
        """Remove a slash command from Discord API"""
        r = await remove_slash_command(self.bot.user.id, self.bot.http.token, guildid, ID)
        if not 200 <= r <= 204:
            self.bot.log.warn(f"[slash_command] Something went wrong when deleting custom command {ID}: Discord answered {r}")
            return False
        print(type(self.bot.slashClient.commands['hello']))
        self.bot.slashClient.commands = {k: v for k, v in self.bot.slashClient.commands.items() if v.id != ID}
        return 200 <= r <= 204

    async def disc_get_command(self, guildid: int, name: str) -> typing.Optional[dict]:
        """Get a slash command from Discord API"""
        g_cmds: list[dict] = await get_all_commands(self.bot.user.id, self.bot.http.token, guild_id=guildid)
        result = [x for x in g_cmds if x['name'] == name]
        return result[0] if result else None

def setup(bot):
    bot.add_cog(Slash(bot))
