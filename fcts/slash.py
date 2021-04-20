import asyncio
import copy
import datetime

import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import get_all_commands

from utils import MyContext, zbot
from fcts import args, checks


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
        cmds: dict[list[int]] = dict()
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
        self.bot.log.error("[on_slash_command] New error:", exc_info=True)
    
    async def test(self, ctx: SlashContext):
        print("HI")
        await ctx.send("GOT IT")
    
    @cog_ext.cog_slash(name="ping")
    async def _slash(self, ctx: SlashContext): # Normal usage.
        await ctx.send(content=f"Pong! (`{round(self.bot.latency*1000)}`ms)")
    
    @cog_ext.cog_slash(name="add-tag")
    async def add_tag(self, ctx: SlashContext, *args, **kwargs):
        await ctx.send(f"args: {args}\nkwargs: {kwargs}")


def setup(bot):
    bot.add_cog(Slash(bot))
