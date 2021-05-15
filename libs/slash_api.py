import json
import time
from typing import Any, Optional
import discord
import aiohttp
import asyncio
from utils import zbot

# {'t': 'INTERACTION_CREATE', 's': 18, 'op': 0, 'd': {'version': 1, 'type': 2, 'token': 'aW50ZXJhY3Rpb246ODQyODY0Njc1NzAzNDg4NTEyOmFWbDFqbHpDY3BWbTdwTmVwbXV2UTVtMG03MFByMTlKaHdTZFJxc1BjSjc3Z3RDaEJIeVRzeXF0dndndURUeWNFTmhMRVIyTnVlQVdtR00xZWFXTFNqS1B1SGpIM2RvOGtEOGdMM2w5U2JlNkxEbVY5bjJQOWpvaGZIdEM0U1hW', 'member': {'user': {'username': 'Z_Speeder', 'public_flags': 0, 'id': '842823322072907776', 'discriminator': '9983', 'avatar': None}, 'roles': [], 'premium_since': None, 'permissions': '17179869183', 'pending': False, 'nick': None, 'mute': False, 'joined_at': '2021-05-14T18:00:26.886000+00:00', 'is_pending': False, 'deaf': False, 'avatar': None}, 'id': '842864675703488512', 'guild_id': '842823690999955481', 'data': {'name': 'ping', 'id': '789420712669872131'}, 'channel_id': '842823690999955483', 'application_id': '436835675304755200'}}

class CustomRoute(discord.http.Route): # type: ignore
    """discord.py's Route but changed ``BASE`` to use at slash command."""
    BASE = "https://discord.com/api/v8"

class SlashCommandRequest:
    def __init__(self, bot: zbot):
        self._discord = bot
        self.application_id = self._discord.user.id

    def put_slash_commands(self, slash_commands: list, guild_id):
        """
        Sends a slash command put request to the Discord API
        ``slash_commands`` must contain all the commands
        :param slash_commands: List of all the slash commands to make a put request to discord with.
        :param guild_id: ID of the guild to set the commands on. Pass `None` for the global scope.
        """
        return self.command_request(
            method="PUT", guild_id = guild_id, json = slash_commands
        )

    def remove_slash_command(self, guild_id, cmd_id):
        """
        Sends a slash command delete request to Discord API.
        :param guild_id: ID of the guild to add command. Pass `None` to add global command.
        :param cmd_id: ID of the command.
        :return: Response code of the request.
        """
        return self.command_request(
            method="DELETE", guild_id=guild_id, url_ending=f"/{cmd_id}"
        )

    def get_all_commands(self, guild_id=None):
        """
        Sends a slash command get request to Discord API for all commands.
        :param guild_id: ID of the guild to add command. Pass `None` to add global command.
        :return: JSON Response of the request.
        """
        return self.command_request(method="GET", guild_id=guild_id)

    def get_all_guild_commands_permissions(self, guild_id):
        """
        Sends a slash command get request to Discord API for all permissions of a guild.
        :param guild_id: ID of the target guild to get registered command permissions of.
        :return: JSON Response of the request.
        """
        return self.command_request(method="GET", guild_id=guild_id, url_ending="/permissions")

    def update_guild_commands_permissions(self, guild_id, perms_dict):
        """
        Sends a slash command put request to the Discord API for setting all command permissions of a guild.
        :param guild_id: ID of the target guild to register command permissions.
        :return: JSON Response of the request.
        """
        return self.command_request(method="PUT", guild_id=guild_id, json=perms_dict, url_ending="/permissions")

    def add_slash_command(
        self, guild_id, cmd_name: str, description: str, options: list = None
    ):
        """
        Sends a slash command add request to Discord API.
        :param guild_id: ID of the guild to add command. Pass `None` to add global command.
        :param cmd_name: Name of the command. Must be 3 or longer and 32 or shorter.
        :param description: Description of the command.
        :param options: List of the function.
        :return: JSON Response of the request.
        """
        base = {"name": cmd_name, "description": description, "options": options or []}
        return self.command_request(json=base, method="POST", guild_id = guild_id)

    def command_request(self, method, guild_id, url_ending="", **kwargs):
        r"""
        Sends a command request to discord (post, get, delete, etc)
        :param method: HTTP method.
        :param guild_id: ID of the guild to make the request on. `None` to make a request on the global scope.
        :param url_ending: String to append onto the end of the url.
        :param \**kwargs: Kwargs to pass into discord.py's `request function <https://github.com/Rapptz/discord.py/blob/master/discord/http.py#L134>`_
        """
        url = f"/applications/{self.application_id}"
        url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
        url += url_ending
        route = CustomRoute(method, url)
        return self._discord.http.request(route, **kwargs)

    def post_followup(self, _resp, token, files: list[discord.File] = None):
        """
        Sends command followup response POST request to Discord API.
        :param _resp: Command response.
        :type _resp: dict
        :param token: Command message token.
        :param files: Files to send. Default ``None``
        :type files: List[discord.File]
        :return: Coroutine
        """
        if files:
            return self.request_with_files(_resp, files, token, "POST")
        return self.command_response(token, True, "POST", json=_resp)

    def post_initial_response(self, _resp, interaction_id, token):
        """
        Sends an initial "POST" response to the Discord API.
         
        :param _resp: Command response.
        :type _resp: dict
        :param interaction_id: Interaction ID.
        :param token: Command message token.
        :return: Coroutine
        """
        return self.command_response(token, False, "POST", interaction_id, json=_resp)

    def command_response(self, token, use_webhook, method, interaction_id= None, url_ending = "", **kwargs):
        """
        Sends a command response to discord (POST, PATCH, DELETE)
        :param token: Interaction token
        :param use_webhook: Whether to use webhooks
        :param method: The HTTP request to use
        :param interaction_id: The id of the interaction
        :param url_ending: String to append onto the end of the url.
        :param *kwargs: Kwargs to pass into discord.py's `request function <https://github.com/Rapptz/discord.py/blob/master/discord/http.py#L134>`_
        :return: Coroutine
        """
        if not use_webhook and not interaction_id:
            raise ValueError("Internal Error! interaction_id must be set if use_webhook is False")
        req_url = f"/webhooks/{self.application_id}/{token}" if use_webhook else f"/interactions/{interaction_id}/{token}/callback"
        req_url += url_ending
        route = CustomRoute(method, req_url)
        return self._discord.http.request(route, **kwargs)

    def request_with_files(self, _resp, files: list[discord.File], token, method, url_ending = ""):

        form = aiohttp.FormData()
        form.add_field("payload_json", json.dumps(_resp))
        for x in range(len(files)):
            name = f"file{x if len(files) > 1 else ''}"
            sel = files[x]
            form.add_field(name, sel.fp, filename=sel.filename, content_type="application/octet-stream")
        return self.command_response(token, True, method, data=form, files=files, url_ending=url_ending)

    def edit(self, _resp, token, message_id="@original", files: list[discord.File] = None):
        """
        Sends edit command response PATCH request to Discord API.
        :param _resp: Edited response.
        :type _resp: dict
        :param token: Command message token.
        :param message_id: Message ID to edit. Default initial message.
        :param files: Files. Default ``None``
        :type files: List[discord.File]
        :return: Coroutine
        """
        req_url = f"/messages/{message_id}"
        if files:
            return self.request_with_files(_resp, files, token, "PATCH", url_ending = req_url)
        return self.command_response(token, True, "PATCH", url_ending = req_url, json=_resp)

    def delete(self, token, message_id="@original"):
        """
        Sends delete command response POST request to Discord API.
        :param token: Command message token.
        :param message_id: Message ID to delete. Default initial message.
        :return: Coroutine
        """
        req_url = f"/messages/{message_id}"
        return self.command_response(token, True, "DELETE", url_ending = req_url)


class SlashClient:
    def __init__(self, bot: zbot):
        self.bot = bot
        self.bot_token = bot.http.token
        self._http = SlashCommandRequest(self.bot)
    
    async def add_command(self, guild_id: int, cmd_name: str, description: str):
        """Add a custom slash command for a specific guild
        guild_id can be None for a global slash command"""
        url = f"https://discord.com/api/v8/applications/{self.bot.user.id}"
        url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
        base = {
            "name": cmd_name,
            "description": description,
            "options": []
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers={"Authorization": f"Bot {self.bot_token}"}, json=base) as resp:
                if resp.status == 429:
                    _json = await resp.json()
                    await asyncio.sleep(_json["retry_after"])
                    return await self.add_command(guild_id, cmd_name, description)
                if not 200 <= resp.status < 300:
                    resp.raise_for_status()
                return await resp.json()
    
    async def remove_command(self, guild_id: int, cmd_id: int) -> int:
        """Remove a custom slash command from a specific guild
        guild_id can be None for a global slash command"""
        url = f"https://discord.com/api/v8/applications/{self.bot.user.id}"
        url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
        url += f"/{cmd_id}"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers={"Authorization": f"Bot {self.bot_token}"}) as resp:
                if resp.status == 429:
                    _json = await resp.json()
                    await asyncio.sleep(_json["retry_after"])
                    return await self.remove_command(guild_id, cmd_id)
                if not 200 <= resp.status < 300:
                    resp.raise_for_status()
                return resp.status
    
    async def get_all_commands(self, guild_id: int = None):
        """Get every command of a guild (or every global command)"""
        url = f"https://discord.com/api/v8/applications/{self.bot.user.id}"
        url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Authorization": f"Bot {self.bot_token}"}) as resp:
                if resp.status == 429:
                    _json = await resp.json()
                    await asyncio.sleep(_json["retry_after"])
                    return await self.get_all_commands(guild_id)
                if not 200 <= resp.status < 300:
                    resp.raise_for_status()
                return await resp.json()

class SlashCommand:
    def __init__(self, data: dict[str, str]):
        self.id: int = int(data['id'])
        self.name: str = data['name']

class SlashContext:
    def __init__(self, data: dict, client: SlashClient):
        self._data: dict[str, Any] = data
        self.bot = client.bot
        self.token: str = data['token']
        self.author: dict[str, Any] = data['member']
        self.guild_id: Optional[int] = int(data['guild_id']) if 'guild_id' in data else None
        self.channel_id: Optional[int] = int(data['channel_id']) if 'channel_id' in data else None
        self.interaction_id: int = int(data['id'])
        self.application_id: int = int(data['application_id'])
        self.command = SlashCommand(data['data'])
        self.created_at = time.time()

        self.message = None  # Should be set later
        self._http = client._http
        self.deferred = False
        self._deferred_hidden = False  # To check if the patch to the deferred response matches
        self.responded = False
    
    async def send(self,
                   content: str = "", *,
                   embed: discord.Embed = None,
                   embeds: list[discord.Embed] = None,
                   tts: bool = False,
                   file: discord.File = None,
                   files: list[discord.File] = None,
                   allowed_mentions: discord.AllowedMentions = None,
                   hidden: bool = False):
        """
        Sends response of the slash command.
        .. warning::
            - Since Release 1.0.9, this is completely changed. If you are migrating from older version, please make sure to fix the usage.
            - You can't use both ``embed`` and ``embeds`` at the same time, also applies to ``file`` and ``files``.
            - If you send files in the initial response, this will defer if it's not been deferred, and then PATCH with the message
        :param content:  Content of the response.
        :type content: str
        :param embed: Embed of the response.
        :type embed: discord.Embed
        :param embeds: Embeds of the response. Maximum 10.
        :type embeds: List[discord.Embed]
        :param tts: Whether to speak message using tts. Default ``False``.
        :type tts: bool
        :param file: File to send.
        :type file: discord.File
        :param files: Files to send.
        :type files: List[discord.File]
        :param allowed_mentions: AllowedMentions of the message.
        :type allowed_mentions: discord.AllowedMentions
        :param hidden: Whether the message is hidden, which means message content will only be seen to the author.
        :type hidden: bool
        """
        if embed and embeds:
            raise ValueError("You can't use both `embed` and `embeds`!")
        if embed:
            embeds = [embed]
        if embeds:
            if not isinstance(embeds, list):
                raise ValueError("Provide a list of embeds.")
            elif len(embeds) > 10:
                raise ValueError("Do not provide more than 10 embeds.")
        if file and files:
            raise ValueError("You can't use both `file` and `files`!")
        if file:
            files = [file]

        base = {
            "content": content,
            "tts": tts,
            "embeds": [x.to_dict() for x in embeds] if embeds else [],
            "allowed_mentions": allowed_mentions.to_dict() if allowed_mentions
            else self.bot.allowed_mentions.to_dict() if self.bot.allowed_mentions else {}
        }
        if hidden:
            base["flags"] = 64

        initial_message = False
        if not self.responded:
            initial_message = True
            if files and not self.deferred:
                await self.defer(hidden=hidden)
            if self.deferred:
                if self._deferred_hidden != hidden:
                    self.bot.log.warn(
                        "Deferred response might not be what you set it to! (hidden / visible) "
                        "This is because it was deferred in a different state."
                    )
                resp = await self._http.edit(base, self.token, files=files)
                self.deferred = False
            else:
                json_data = {
                    "type": 4,
                    "data": base
                }
                await self._http.post_initial_response(json_data, self.interaction_id, self.token)
                if not hidden:
                    resp = await self._http.edit({}, self.token)
                else:
                    resp = {}
            self.responded = True
        else:
            resp = await self._http.post_followup(base, self.token, files=files)
        if files:
            for file in files:
                file.close()
    
    async def defer(self, hidden: bool = False):
        """
        'Defers' the response, showing a loading state to the user
        :param hidden: Whether the deferred response should be ephemeral . Default ``False``.
        """
        if self.deferred or self.responded:
            raise Exception("You have already responded to this command!")
        base: dict[str, Any] = {"type": 5}
        if hidden:
            base["data"] = {"flags": 64}
            self._deferred_hidden = True
        await self._http.post_initial_response(base, self.interaction_id, self.token)
        self.deferred = True