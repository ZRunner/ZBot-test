from utils import zbot, MyContext
from fcts.checks import is_fun_enabled
import discord
import random
import operator
import string
import importlib
import re
import typing
import datetime
import geocoder
import aiohttp
import copy
import emoji as emojilib
from difflib import get_close_matches
from discord.ext import commands
from tzwhere import tzwhere
from pytz import timezone

from fcts import emojis, checks, args
importlib.reload(emojis)
importlib.reload(checks)
importlib.reload(args)

cmds_list = ['count_msg','ragequit','pong','run','nope','blame','party','bigtext','shrug','gg','money','pibkac','osekour','me','kill','cat','happy-birthday','rekt','thanos','nuke','pikachu','pizza','google','loading','piece','roll','afk', 'bubble-wrap','reverse']


async def can_say(ctx: MyContext):
    if not ctx.bot.database_online:
        return ctx.channel.permissions_for(ctx.author).administrator
    else:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author,"say")

async def can_use_cookie(ctx: MyContext):
#                            Z_runner           neil3000            Awhikax           Adri         Theventreur         Catastrophix        Platon_Neutron      megat69            Aragorn1202
    return ctx.author.id in [279568324260528128,278611007952257034,281404141841022976,409470110131027979,229194747862843392,438372385293336577,286827468445319168,517762101859844106,375598088850505728]

class Fun(commands.Cog):
    """Add some fun commands, no obvious use. You can disable this module with the 'enable_fun' option (command 'config')"""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.fun_opt = dict()
        self.file = "fun"
        self.tz = tzwhere.tzwhere(forceTZ=True)
        self.afk_guys = dict()
        self.nasa_pict:dict = None
        try:
            self.utilities = self.bot.get_cog("Utilities")
        except:
            pass

    async def cache_update(self,id,value):
        self.fun_opt[str(id)] = value

    @commands.Cog.listener()
    async def on_ready(self):
            self.utilities = self.bot.get_cog("Utilities")

    async def is_on_guild(self,user,guild):
        if self.bot.user.id == 436835675304755200:
            return True
        if user.id in [279568324260528128,392766377078816789,281404141841022976]:
            return True
        server = self.bot.get_guild(guild)
        if server is not None:
            return user in server.members
        return False
    
    

    @commands.command(name='fun')
    async def main(self,ctx: MyContext):
        """Get a list of all fun commands
        
        ..Doc fun.html"""
        if not await is_fun_enabled(ctx):
            if ctx.bot.database_online:
                await ctx.send(await self.bot._(ctx.channel,"fun","no-fun"))
            else:
                await ctx.send(await self.bot._(ctx.channel,"fun","no-database"))
            return
        title = await self.bot._(ctx.channel,"fun","fun-list")
        if self.bot.current_event=="fish":
            title = ":fish: "+title
        text = str()
        for cmd in sorted(self.get_commands(),key=operator.attrgetter('name')):
            if cmd.name in cmds_list and cmd.enabled:
                if cmd.help is not None:
                    text+="\n- {} *({})*".format(cmd.name,cmd.help.split('\n')[0])
                else:
                    text+="\n- {}".format(cmd.name)
                if type(cmd)==commands.core.Group:
                    for cmds in cmd.commands:
                        text+="\n    - {} *({})*".format(cmds.name,cmds.help)
        if ctx.can_send_embed:
            emb = await ctx.bot.get_cog('Embeds').Embed(title=title,desc=text,color=ctx.bot.get_cog('Help').help_color,time=ctx.message.created_at).create_footer(ctx)
            return await ctx.send(embed=emb.discord_embed())
        await ctx.send(title+text)

    @commands.command(name='roll',hidden=True)
    @commands.check(is_fun_enabled)
    async def roll(self,ctx,*,options):
        """Selects an option at random from a given list
        The options must be separated by a comma `,`
        
        ..Example roll Play Minecraft, play Star Citizens, do homeworks
        
        ..Doc fun.html#roll"""
        liste = list(set([x for x in [x.strip() for x in options.split(',')] if len(x) > 0]))
        if len(liste) == 0:
            return await ctx.send(await self.bot._(ctx.channel,"fun","no-roll"))
        elif len(liste) == 1:
            return await ctx.send(await self.bot._(ctx.channel,"fun","not-enough-roll"))
        # choosen = random.choice(liste).replace('@everyone','@​everyone').replace('@here','@​here')
        choosen = random.choice(liste)
        await ctx.send(choosen)

    @commands.command(name="cookie",aliases=['cookies'],hidden=True)
    @commands.check(can_use_cookie)
    @commands.check(is_fun_enabled)
    async def cookie(self,ctx: MyContext):
        """COOKIE !!!"""
        if ctx.author.id == 375598088850505728:
            await ctx.send(file=await self.utilities.find_img("cookie-target.gif"))
        else:
            await ctx.send(str(await self.bot._(ctx.guild,"fun","cookie")).format(ctx.author.mention,self.bot.get_cog('Emojis').customEmojis['cookies_eat']))

    @commands.command(name="reverse", hidden=True)
    @commands.check(is_fun_enabled)
    async def reverse(self, ctx: MyContext, *, text:str):
        """Reverse the letters of a message
        
        ..Doc fun.html#reverse"""
        await ctx.send(text[::-1])

    @commands.command(name="count_msg",hidden=True)
    @commands.check(is_fun_enabled)
    @commands.cooldown(5, 30, type=commands.BucketType.channel)
    async def count(self, ctx:MyContext, limit:typing.Optional[int]=1000, user:typing.Optional[discord.User]=None, channel:typing.Optional[discord.TextChannel]=None):
        """Count the number of messages sent by the user
You can specify a verification limit by adding a number in argument (up to 1.000.000)

        ..Example count_msg

        ..Example count_msg Z_runner #announcements

        ..Example count_msg 300 someone
        
        ..Doc fun.html#count-messages"""
        MAX = 20000
        if channel is None:
            channel = ctx.channel
        if not channel.permissions_for(ctx.author).read_message_history:
            await ctx.send(await self.bot._(ctx.channel,'fun','count-5'))
            return
        if user is not None and user.name.isnumeric() and limit==1000:
            limit = int(user.name)
            user = None
        if limit > MAX:
            await ctx.send(await self.bot._(ctx.channel,"fun","count-2",l=MAX,e=self.bot.get_cog('Emojis').customEmojis['wat']))
            return
        if ctx.guild is not None and not channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.bot._(channel,"fun","count-3"))
            return
        if user is None:
            user = ctx.author
        counter = 0
        tmp = await ctx.send(await self.bot._(ctx.channel,'fun','count-0'))
        m = 0
        async for log in channel.history(limit=limit):
            m += 1
            if log.author == user:
                counter += 1
        r = round(counter*100/m,2)
        if user==ctx.author:
            await tmp.edit(content = await self.bot._(ctx.channel,'fun','count-1',limit=m,x=counter,p=r))
        else:
            await tmp.edit(content = await self.bot._(ctx.channel,'fun','count-4', limit=m,user=user.display_name,x=counter,p=r))

    @commands.command(name="ragequit",hidden=True)
    @commands.check(is_fun_enabled)
    async def ragequit(self,ctx: MyContext):
        """To use when you get angry - limited to certain members

        ..Doc fun.html#ragequit"""
        await ctx.send(file=await self.utilities.find_img('ragequit{0}.gif'.format(random.randint(1,6))))

    @commands.command(name="run",hidden=True)
    @commands.check(is_fun_enabled)
    async def run(self,ctx: MyContext):
        """"Just... run... very... fast
        
        ..Doc fun.html#run"""
        await ctx.send("ε=ε=ε=┏( >_<)┛")

    @commands.command(name="pong",hidden=True)
    @commands.check(is_fun_enabled)
    async def pong(self,ctx: MyContext):
        """Ping !
        
        ..Doc fun.html#pong"""
        await ctx.send("Ping !")

    @commands.command(name="nope",hidden=True)
    @commands.check(is_fun_enabled)
    async def nope(self,ctx: MyContext):
        """Use this when you do not agree with someone else
        
        ..Doc fun.html#nope"""
        await ctx.send(file=await self.utilities.find_img('nope.png'))
        if self.bot.database_online:
            try:
                if await self.bot.get_cog("Servers").staff_finder(ctx.author,'say'):
                    await self.utilities.suppr(ctx.message)
            except commands.CommandError: # user can't use 'say'
                pass

    @commands.command(name="blame",hidden=True)
    @commands.check(is_fun_enabled)
    async def blame(self,ctx,name):
        """Blame someone
        Use 'blame list' command to see every available name *for you*
        
        ..Example blame discord
        
        ..Doc fun.html#blame"""
        l1 = ['discord','mojang','zbot','google','youtube'] # tout le monde
        l2 = ['tronics','patate','neil','reddemoon','aragorn1202','platon'] # frm
        l3 = ['awhikax','aragorn','adri','zrunner'] # zbot
        l4 = ['benny'] #benny
        name = name.lower()
        if name in l1:
            await ctx.send(file=await self.utilities.find_img('blame-{}.png'.format(name)))
        elif name in l2:
            if await self.is_on_guild(ctx.author,391968999098810388): # fr-minecraft
                await ctx.send(file=await self.utilities.find_img('blame-{}.png'.format(name)))
        elif name in l3:
            if await self.is_on_guild(ctx.author,356067272730607628): # Zbot server
                await ctx.send(file=await self.utilities.find_img('blame-{}.png'.format(name)))
        elif name in l4:
            if await self.is_on_guild(ctx.author,523525264517496834): # Benny Support
                await ctx.send(file=await self.utilities.find_img('blame-{}.png'.format(name)))
        elif name in ['help','list']:
            liste = l1
            if await self.is_on_guild(ctx.author,391968999098810388): # fr-minecraft
                liste += l2
            if await self.is_on_guild(ctx.author,356067272730607628): # Zbot server
                liste += l3
            if await self.is_on_guild(ctx.author,523525264517496834): # Benny Support
                liste += l4
            txt = "- "+"\n- ".join(sorted(liste))
            title = str(await self.bot._(ctx.channel,"fun","blame-0")).format(ctx.author)
            if ctx.can_send_embed:
                emb = self.bot.get_cog("Embeds").Embed(title=title,desc=txt,color=self.bot.get_cog("Help").help_color).update_timestamp()
                await ctx.send(embed=emb.discord_embed())
            else:
                await ctx.send("__{}:__\n\n{}".format(title,txt))

    @commands.command(name="kill",hidden=True)
    @commands.guild_only()
    @commands.check(is_fun_enabled)
    async def kill(self,ctx,*,name=None):
        """Just try to kill someone with a fun message
        
        ..Example kill herobrine
        
        ..Doc fun.html#kill"""
        if name is None:
            victime = ctx.author.display_name
            ex = ctx.author.display_name.replace(" ","_")
        else:
            victime = name
            ex = name.replace(" ","_")
        author = ctx.author.mention
        liste = await self.bot._(ctx.channel,"kill","list")
        msg = random.choice(liste)
        tries = 0
        while '{0}' in msg and name is None and tries<50:
            msg = random.choice(liste)
            tries += 1
        await ctx.send(msg.format(author,victime,ex))

    @commands.command(name="arapproved",aliases=['arapprouved'],hidden=True)
    @commands.check(lambda ctx: ctx.author.id in [375598088850505728,279568324260528128])
    async def arapproved(self,ctx: MyContext):
        await ctx.send(file=await self.utilities.find_img("arapproved.png"))

    @commands.command(name='party',hidden=True)
    @commands.check(is_fun_enabled)
    async def party(self,ctx: MyContext):
        """Sends a random image to make the server happier
        
        ..Doc fun.html#party"""
        r = random.randrange(5)+1
        if r == 1:
            await ctx.send(file=await self.utilities.find_img('cameleon.gif'))
        elif r == 2:
            await ctx.send(file=await self.utilities.find_img('discord_party.gif'))
        elif r == 3:
            await ctx.send(file=await self.utilities.find_img('parrot.gif'))
        elif r == 4:
            e = self.bot.get_cog('Emojis').customEmojis['blob_dance']
            await ctx.send(e*5)
        elif r == 5:
            await ctx.send(file=await self.utilities.find_img('cameleon.gif'))

    @commands.command(name="cat",hidden=True)
    @commands.check(is_fun_enabled)
    async def cat_gif(self,ctx: MyContext):
        """Wow... So cuuuute !
        
        ..Doc fun.html#cat"""
        await ctx.send(random.choice(['http://images6.fanpop.com/image/photos/40800000/tummy-rub-kitten-animated-gif-cute-kittens-40838484-380-227.gif',
        'http://25.media.tumblr.com/7774fd7794d99b5998318ebd5438ba21/tumblr_n2r7h35U211rudcwro1_400.gif',
        'https://www.2tout2rien.fr/wp-content/uploads/2014/10/37-pestes-de-chats-mes-bonbons.gif',
        'http://coquelico.c.o.pic.centerblog.net/chat-peur.gif',
        'https://tenor.com/view/nope-bye-cat-leave-done-gif-12387359']))
    
    @commands.command(name="happy-birthday", hidden=True, aliases=['birthday', 'hb'])
    @commands.check(is_fun_enabled)
    async def birthday_gif(self,ctx: MyContext):
        """How many candles this year?
        
        ..Doc fun.html#birthdays"""
        await ctx.send(random.choice(['https://tenor.com/view/happy-birthday-cat-cute-birthday-cake-second-birthday-gif-16100991',
        'https://tenor.com/view/happy-birthday-birthday-cake-goat-licking-lick-gif-15968273',
        'https://tenor.com/view/celebracion-gif-4928008',
        'https://tenor.com/view/kitty-birthday-birthday-kitty-happy-birthday-happy-birthday-to-you-hbd-gif-13929089',
        'https://tenor.com/view/happy-birthday-happy-birthday-to-you-hbd-birthday-celebrate-gif-13366300']))
    
    @commands.command(name="bigtext",hidden=True)
    @commands.check(is_fun_enabled)
    async def big_text(self,ctx,*,text):
        """If you wish to write bigger

        ..Example bigtext Hi world! I'm 69?!
        
        ..Doc fun.html#bigtext"""
        # contenu = await self.bot.get_cog('Utilities').clear_msg(text,ctx=ctx,emojis=False)
        contenu = await commands.clean_content().convert(ctx, text)
        text = ""
        Em = self.bot.get_cog('Emojis')
        mentions = [x.group(1) for x in re.finditer(r'(<(?:@!?&?|#|a?:[a-zA-Z0-9_]+:)\d+>)',ctx.message.content)]
        content = "¬¬".join(contenu.split("\n"))
        for x in mentions:
            content = content.replace(x,'¤¤')
        for l in content:
            l = l.lower()
            if l in string.ascii_letters:
                item = discord.utils.get(ctx.bot.emojis,id=Em.alphabet[string.ascii_letters.index(l)])
            elif l in string.digits:
                item = discord.utils.get(ctx.bot.emojis,id=Em.numbers[int(l)])
            else:
                try:
                    item = discord.utils.get(ctx.bot.emojis,id=Em.chars[l])
                except KeyError:
                    item = l
            text += str(item)+'¬'
        text = text.replace("¬¬","\n")
        for m in mentions:
            text = text.replace('¤¬¤',m,1)
        text = text.split('¬')[:-1]
        text1 = list()
        for line in text:
            text1.append(line)
            caract = len("".join(text1))
            if caract > 1970:
                await ctx.send("".join(text1))
                text1 = []
        if text1 != []:
            await ctx.send(''.join(text1))
        try:
            if ctx.bot.database_online and await self.bot.get_cog("Servers").staff_finder(ctx.author,'say'):
                await self.bot.get_cog("Utilities").suppr(ctx.message)
        except commands.CommandError: # user can't use 'say'
            pass
        self.bot.log.debug("{} used bigtext to say {}".format(ctx.author.id,text))
    
    @commands.command(name="shrug",hidden=True)
    @commands.check(is_fun_enabled)
    async def shrug(self,ctx: MyContext):
        """Don't you know? Neither do I
        
        ..Doc fun.html#shrug"""
        await ctx.send(file=await self.utilities.find_img('shrug.gif'))
    
    @commands.command(name="rekt",hidden=True)
    @commands.check(is_fun_enabled)
    async def rekt(self,ctx: MyContext):
        await ctx.send(file=await self.utilities.find_img('rekt.jpg'))

    @commands.command(name="gg",hidden=True)
    @commands.check(is_fun_enabled)
    async def gg(self,ctx: MyContext):
        """Congrats! You just found something!
        
        ..Doc fun.html#congrats"""
        await ctx.send(file=await self.utilities.find_img('gg.gif'))
    
    @commands.command(name="money",hidden=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.cooldown(10, 60, commands.BucketType.guild)
    @commands.check(is_fun_enabled)
    async def money(self,ctx: MyContext):
        """Money gif. Cuz we all love money, don't we?
        
        ..Doc fun.html#money"""
        await ctx.send(file=await self.utilities.find_img('money.gif'))
    
    @commands.command(name="pibkac",hidden=True)
    @commands.check(is_fun_enabled)
    async def pibkac(self,ctx: MyContext):
        """Where comes that bug from?
        
        ..Doc fun.html#pibkac"""
        await ctx.send(file=await self.utilities.find_img('pibkac.png'))
    
    @commands.command(name="osekour",hidden=True,aliases=['helpme','ohmygod'])
    @commands.check(is_fun_enabled)
    async def osekour(self,ctx: MyContext):
        """Does anyone need help?
        
        ..Doc fun.html#heeelp"""
        l = await self.bot._(ctx.channel,"fun","osekour")
        await ctx.send(random.choice(l))

    @commands.command(name="say")
    @commands.guild_only()
    @commands.check(can_say)
    async def say(self,ctx:MyContext,channel:typing.Optional[discord.TextChannel] = None, *, text):
        """Let the bot say something for you
        You can specify a channel where the bot must send this message. If channel is None, the current channel will be used
        
        ..Example say #chat Hi I'm invading Earth

        ..Example say Booh!
        
        ..Doc miscellaneous.html#say"""
        if channel is None:
            channel = ctx.channel
        elif not (channel.permissions_for(ctx.author).read_messages and channel.permissions_for(ctx.author).send_messages and channel.guild == ctx.guild):
            await ctx.send(await self.bot._(ctx.guild, 'fun', 'say-no-perm', channel=channel.mention))
            return
        if self.bot.zombie_mode:
            return
        if m := re.search(r"(?:i am|i'm) ([\w\s]+)", text, re.DOTALL | re.IGNORECASE):
            if m.group(1).lower() != "a bot":
                first_words = ['dumb', 'really dumb','stupid', 'gay', 'idiot', 'shit', 'trash']
                words = list()
                for w in first_words:
                    words += [w, w+' bot', w.upper()]
                if word := get_close_matches(m.group(1), words, n=1, cutoff=0.8):
                    await ctx.send(f"Yeah we know you are {word[0]}")
                    return
        try:
            text = await self.bot.get_cog("Utilities").clear_msg(text, ctx=ctx)
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e, ctx)
            return
        try:
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(str(await self.bot._(ctx.guild.id, 'fun', 'no-say'))+random.choice([' :confused:', '', '', '']))
            await channel.send(text)
            await self.bot.get_cog("Utilities").suppr(ctx.message)
        except:
            pass

    @commands.command(name="me",hidden=True)
    @commands.check(is_fun_enabled)
    async def me(self,ctx,*,text):
        """No U
        
        ..Doc fun.html#me"""
        text = "*{} {}*".format(ctx.author.display_name,text)
        text = await self.bot.get_cog("Utilities").clear_msg(text,ctx=ctx)
        await ctx.send(text)
        try:
            if self.bot.database_online and await self.bot.get_cog("Servers").staff_finder(ctx.author,"say"):
                await self.bot.get_cog("Utilities").suppr(ctx.message)
        except commands.CommandError: # user can't use 'say'
            pass
    
    @commands.command(name="react")
    @commands.check(can_say)
    async def react(self, ctx:MyContext, message:discord.Message, *, reactions):
        """Add reaction(s) to a message. Server emojis also work.
        
        ..Example react 375246790301057024-790177026232811531 :ok:

        ..Example react https://discord.com/channels/125723125685026816/375246790301057024/790177026232811531 :party: :money:

        ..Doc fun.html#react"""
        channel = message.channel
        if not (channel.permissions_for(ctx.author).read_messages and channel.permissions_for(ctx.author).add_reactions and (channel.guild is None or channel.guild==ctx.guild)):
            await ctx.send(await self.bot._(ctx.channel,'fun','say-no-perm',channel=channel.mention))
            return
        for r in reactions.split():
            try:
                e = await commands.EmojiConverter().convert(ctx,r)
                await message.add_reaction(e)
            except:
                try:
                    await message.add_reaction(r)
                except discord.errors.HTTPException:
                    await ctx.send(await self.bot._(ctx.channel,'fun','no-emoji'))
                    return
                except Exception as e:
                    await self.bot.get_cog("Errors").on_error(e,ctx)
                    continue
        await self.bot.get_cog("Utilities").suppr(ctx.message)
    
    @commands.command(name="nuke",hidden=True)
    @commands.check(is_fun_enabled)
    async def nuke(self,ctx: MyContext):
        """BOOOM
        
        ..Doc fun.html#nuke"""
        await ctx.send(file=await self.utilities.find_img('nuke.gif'))
    
    @commands.command(name="pikachu",hidden=True)
    @commands.check(is_fun_enabled)
    async def pikachu(self,ctx: MyContext):
        """Pika-pika ?
        
        ..Doc fun.html#pikachu"""
        await ctx.send(file=await self.utilities.find_img(random.choice(['cookie-pikachu.gif','pika1.gif'])))
    
    @commands.command(name="pizza",hidden=True)
    @commands.check(is_fun_enabled)
    async def pizza(self,ctx: MyContext):
        """Hey, do U want some pizza?
        
        ..Doc fun.html#pizza"""
        await ctx.send(file=await self.utilities.find_img('pizza.gif'))
    
    @commands.command(name="google", hidden=True, aliases=['lmgtfy'])
    @commands.check(is_fun_enabled)
    async def lmgtfy(self,ctx,*,search):
        """How to use Google
        
        ..Doc fun.html#lmgtfy"""
        link = "http://lmgtfy.com/?q="+search.replace("\n","+").replace(" ","+")
        await ctx.send('<'+link+'>')
        await self.bot.get_cog('Utilities').suppr(ctx.message)
    
    @commands.command(name="loading",hidden=True)
    @commands.check(is_fun_enabled)
    async def loading(self,ctx: MyContext):
        """time goes by soooo slowly...
        
        ..Doc fun.html#loading"""
        await ctx.send(file=await self.utilities.find_img('loading.gif'))
    
    @commands.command(name="thanos",hidden=True)
    @commands.check(is_fun_enabled)
    async def thanos(self, ctx: MyContext, *, name: str = None):
        """SNAP! Will you be lucky enough to survive?
        
        ..Doc fun.html#thanos"""
        name = name or ctx.author.mention
        await ctx.send(random.choice(await self.bot._(ctx.channel,"fun","thanos")).format(name))
    
    @commands.command(name="piece",hidden=True,aliases=['coin','flip'])
    @commands.check(is_fun_enabled)
    async def piece(self,ctx: MyContext):
        """Heads or tails?
        
        ..Doc fun.html#piece"""
        if random.random() < 0.04:
            await ctx.send(await self.bot._(ctx.channel,"fun","piece-1"))
        else:
            await ctx.send(random.choice(await self.bot._(ctx.channel,"fun","piece-0")))
    
    @commands.command(name="weather",aliases=['météo'])
    @commands.cooldown(4, 30, type=commands.BucketType.guild)
    async def weather(self, ctx:MyContext, *, city:str):
        """Get the weather of a city
        You need to provide the city name in english

        ..Example weather Tokyo
        
        ..Doc miscellaneous.html#hour-weather"""
        city = city.replace(" ","%20")
        async with aiohttp.ClientSession() as session:
            async with session.get("https://welcomer.glitch.me/weather?city="+city) as r:
                if r.status == 200:
                    if r.content_type == 'image/png':
                        if ctx.channel.permissions_for(ctx.me).embed_links:
                            emb = self.bot.get_cog('Embeds').Embed(image="https://welcomer.glitch.me/weather?city="+city,footer_text="From https://welcomer.glitch.me/weather")
                            return await ctx.send(embed=emb.discord_embed())
                        else:
                            return await ctx.send("https://welcomer.glitch.me/weather?city="+city)
                    #except Exception as e:
                    #    await self.bot.get_cog('Errors').on_error(e,ctx)
        await ctx.send(await self.bot._(ctx.channel,"fun","invalid-city"))

    @commands.command(name="hour")
    @commands.cooldown(4, 50, type=commands.BucketType.guild)
    async def hour(self, ctx:MyContext, *, city:str):
        """Get the hour of a city

        ..Example hour Paris
        
        ..Doc miscellaneous.html#hour-weather"""
        if city.lower() in ['mee6','mee6land']:
            return await ctx.send('**Mee6Land/MEE6**:\nEverytime (NoWhere)\n (Mee6Land - lat: unknown - long: unknown)')
        g = geocoder.arcgis(city)
        if not g.ok:
            return await ctx.send(await self.bot._(ctx.channel,"fun","invalid-city"))
        timeZoneStr = self.tz.tzNameAt(g.json['lat'],g.json['lng'],forceTZ=True)
        if timeZoneStr=='uninhabited':
            return await ctx.send(await self.bot._(ctx.channel,"fun","uninhabited-city"))
        timeZoneObj = timezone(timeZoneStr)
        d = datetime.datetime.now(timeZoneObj)
        format_d = await self.bot.get_cog('TimeUtils').date(d,lang=await self.bot._(ctx.channel,"current_lang","current"))
        await ctx.send("**{}**:\n{} ({})\n ({} - lat: {} - long: {})".format(timeZoneStr,format_d,d.tzname(),g.current_result.address,round(g.json['lat'],2),round(g.json['lng'],2)))

    @commands.command(name="tip")
    async def tip(self,ctx:MyContext):
        """Send a tip, a fun fact or something else
        
        ..Doc fun.html#tip"""
        await ctx.send(random.choice(await self.bot._(ctx.guild,"fun","tip-list")))

    @commands.command(name='afk')
    @commands.check(is_fun_enabled)
    @commands.guild_only()
    async def afk(self,ctx,*,reason=""):
        """Make you AFK
        You'll get a nice nickname, because nicknames are cool, aren't they?
        
        ..Doc fun.html#afk"""
        try:
            self.afk_guys[ctx.author.id] = await self.bot.get_cog('Utilities').clear_msg(reason, ctx=ctx)
            if (not ctx.author.display_name.endswith(' [AFK]')) and len(ctx.author.display_name)<26:
                await ctx.author.edit(nick=ctx.author.display_name+" [AFK]")
            await ctx.send(await self.bot._(ctx.guild.id,"fun","afk-done"))
        except discord.errors.Forbidden:
            return await ctx.send(await self.bot._(ctx.guild.id,"fun","afk-no-perm"))
    
    async def user_is_afk(self, user: discord.User) -> bool:
        cond = user.id in self.afk_guys.keys()
        if cond:
            return True
        return isinstance(user, discord.Member) and user.nick and user.nick.endswith(' [AFK]')

    @commands.command(name='unafk')
    @commands.check(is_fun_enabled)
    @commands.guild_only()
    async def unafk(self,ctx: MyContext):
        """Remove you from the AFK system
        Welcome back dude
        
        ..Doc fun.html#afk"""
        if await self.user_is_afk(ctx.author):
            del self.afk_guys[ctx.author.id]
            await ctx.send(await self.bot._(ctx.guild.id,"fun","unafk-done"))
            if ctx.author.nick and ctx.author.nick.endswith(" [AFK]"):
                try:
                    await ctx.author.edit(nick=ctx.author.display_name.replace(" [AFK]",''))                
                except discord.errors.Forbidden:
                    pass
        else:
            await ctx.send(await self.bot._(ctx.guild.id,"fun","unafk-cant"))
    
    async def check_afk(self, msg: discord.Message):
        """Check if someone pinged is afk"""
        if msg.author.bot:
            return
        ctx = await self.bot.get_context(msg)
        if not await is_fun_enabled(ctx, self):
            return
        if self.bot.zombie_mode:
            return
        for member in msg.mentions:
            if await self.user_is_afk(member) and member!=msg.author:
                if member.id not in self.afk_guys or len(self.afk_guys[member.id]) == 0:
                    await msg.channel.send(await self.bot._(msg.guild.id,"fun","afk-user-2"))
                else:
                    reason = await self.bot.get_cog('Utilities').clear_msg(str(await self.bot._(msg.guild.id,"fun","afk-user-1")).format(self.afk_guys[member.id]),ctx=ctx)
                    await msg.channel.send(reason)
        if isinstance(ctx.author, discord.Member) and not await checks.is_a_cmd(msg, self.bot):
            if (ctx.author.nick and ctx.author.nick.endswith(' [AFK]')) or ctx.author.id in self.afk_guys.keys():
                user_config = await self.bot.get_cog('Utilities').get_db_userinfo(["auto_unafk"],[f'`userID`={ctx.author.id}'])
                if user_config is None or (not user_config['auto_unafk']):
                    return
                msg = copy.copy(msg)
                msg.content = (await self.bot.get_prefix(msg))[-1] + 'unafk'
                new_ctx = await self.bot.get_context(msg)
                await self.bot.invoke(new_ctx)


    @commands.command(name='embed',hidden=False)
    @commands.check(checks.has_embed_links)
    @commands.guild_only()
    async def send_embed(self, ctx: MyContext, *, arguments):
        """Send an embed
        Syntax: !embed [channel] key1=\"value 1\" key2=\"value 2\"

        Available keys:
            - title: the title of the embed [256 characters]
            - content: the text inside the box [2048 characters]
            - url: a well-formed url clickable via the title
            - footer: a little text at the bottom of the box [90 characters]
            - image: a well-formed url redirects to an image
            - color: the color of the embed bar (#hex or int)
        If you want to use quotation marks in the texts, it is possible to escape them thanks to the backslash (`\\"`)
        
        You can send the embed to a specific channel by mentionning it at the beginning of the arguments

        ..Example embed #announcements title="Special update!" content="We got an amazing thing for you!\\nPlease check blah blah..." color="#FF0022"

        ..Doc miscellaneous.html#embed
        """
        channel = None
        r = re.search(r'<#(\d+)>', arguments.split(" ")[0])
        if r is not None:
            arguments = " ".join(arguments.split(" ")[1:])
            channel = ctx.guild.get_channel(int(r.group(1)))
        arguments = await args.arguments().convert(ctx, arguments)
        if len(arguments) == 0:
            raise commands.errors.MissingRequiredArgument(ctx.command.clean_params['arguments'])
        destination = ctx.channel if channel is None else channel
        if not (destination.permissions_for(ctx.author).read_messages and destination.permissions_for(ctx.author).send_messages):
            await ctx.send(await self.bot._(ctx.guild,'fun','say-no-perm',channel=destination.mention))
            return
        if not destination.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(await self.bot._(ctx.channel,"fun","embed-invalid-channel"))
        if not destination.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.bot._(ctx.channel,"fun","no-embed-perm"))
        k = {'title':"",'content':"",'url':'','footer':"",'image':'','color':ctx.bot.get_cog('Servers').embed_color}
        for key,value in arguments.items():
            if key=='title':
                k['title'] = value[:255]
            elif key=='content' or key=='url' or key=='image':
                k[key] = value.replace("\\n","\n")
            elif key=='footer':
                k['footer'] = value[:90]
            elif key=='color' or key=="colour":
                c = await args.Color().convert(ctx,value)
                if c is not None:
                    k['color'] = c
        emb = ctx.bot.get_cog("Embeds").Embed(title=k['title'], desc=k['content'], url=k['url'],footer_text=k['footer'],thumbnail=k['image'],color=k['color']).update_timestamp().set_author(ctx.author)
        try:
            await destination.send(embed=emb.discord_embed())
        except Exception as e:
            if isinstance(e,discord.errors.HTTPException) and "In embed.thumbnail.url: Not a well formed URL" in str(e):
                return await ctx.send(await self.bot._(ctx.channel, "fun", "embed-invalid-image"))
            await ctx.send(str(await self.bot._(ctx.channel,"fun","embed-error")).format(e))
        if channel is not None:
            try:
                await ctx.message.delete()
            except:
                pass


    async def add_vote(self,msg):
        if self.bot.database_online and msg.guild is not None:
            emojiz = await self.bot.get_config(msg.guild,'vote_emojis')
        else:
            emojiz = None
        if emojiz is None or len(emojiz) == 0:
            await msg.add_reaction('👍')
            await msg.add_reaction('👎')
            return
        count = 0
        for r in emojiz.split(';'):
            if r.isnumeric():
                d_em = discord.utils.get(self.bot.emojis, id=int(r))
                if d_em is not None:
                    await msg.add_reaction(d_em)
                    count +=1
            elif len(r) > 0:
                await msg.add_reaction(emojilib.emojize(r, use_aliases=True))
                count +=1
        if count == 0:
            await msg.add_reaction('👍')
            await msg.add_reaction('👎')

    @commands.command(name="markdown")
    async def markdown(self, ctx: MyContext):
        """Get help about markdown in Discord
        
        ..Doc miscellaneous.html#markdown"""
        txt = await self.bot._(ctx.channel,'fun','markdown')
        if ctx.can_send_embed:
            await ctx.send(embed=discord.Embed(description=txt))
        else:
            await ctx.send(txt)
    

    @commands.command(name="bubble-wrap", aliases=["papier-bulle", "bw"], hidden=True)
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def bubblewrap(self, ctx:MyContext, width:int=10, height:int=15):
        """Just bubble wrap. Which pops when you squeeze it. That's all.

        Width should be between 1 and 150, height between 1 and 50.

        ..Example bubble-wrap

        ..Example bw 7 20

        ..Doc fun.html#bubble-wrap
        """
        width = min(max(1, width), 150)
        height = min(max(1, height), 50)
        p = "||pop||"
        txt = "\n".join([p*width]*height)
        if len(txt) > 2000:
            await ctx.send(await self.bot._(ctx.channel, "fun", "bbw-too-many"))
            return
        await ctx.send(txt)

    @commands.command(name="nasa")
    @commands.cooldown(5, 60, commands.BucketType.channel)
    async def nasa(self, ctx: MyContext):
        """Send the Picture of The Day by NASA
        
        ..Doc fun.html#nasa"""
        def get_date(string):
            return datetime.datetime.strptime(string, "%Y-%m-%d")
        if ctx.guild and not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "fun", "no-embed-perm"))
            return
        if self.nasa_pict is None or 'date' not in self.nasa_pict or (datetime.datetime.utcnow()-get_date(self.nasa_pict["date"])).total_seconds() > 86400:
            async with aiohttp.ClientSession() as session:
                key = self.bot.others["nasa"]
                async with session.get(f"https://api.nasa.gov/planetary/apod?api_key={key}") as r:
                    data = await r.json()
            if all(field in data for field in ['title', 'url', 'explanation', 'date']):
                self.nasa_pict = data
        if self.nasa_pict is None:
            await ctx.send(await self.bot._(ctx.channel, "fun", "nasa-none"))
            return
        emb = self.bot.get_cog("Embeds").Embed(
            title=self.nasa_pict["title"],
            image=self.nasa_pict["url"],
            url=self.nasa_pict["hdurl"] if self.nasa_pict["media_type"]=="image" else self.nasa_pict["url"],
            desc=self.nasa_pict["explanation"],
            footer_text="Credits: " + self.nasa_pict.get("copyright", "Not copyrighted"),
            time=get_date(self.nasa_pict["date"]))
        await ctx.send(embed=emb)
    
    @commands.command(name="discordjobs", aliases=['discord_jobs', 'jobs.gg'])
    @commands.cooldown(2, 60, commands.BucketType.channel)
    async def discordjobs(self, ctx: MyContext, *, query: str = None):
        """Get the list of available jobs in Discord
        
        ..Example discordjobs
        
        ..Example discordjobs marketing"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.greenhouse.io/v1/boards/discord/jobs") as r:
                data = await r.json()
        if query is not None:
            query = query.lower()
            jobs = [x for x in data['jobs'] if query in x['location']['name'].lower() or query == x['id'] or query in x['title'].lower()]
        else:
            jobs = data['jobs']
        f_jobs = [
            f"[{x['title']}]({x['absolute_url']})" for x in jobs
        ]
        if ctx.can_send_embed:
            _title = await self.bot._(ctx.channel, "fun", "discordjobs-title")
            emb = discord.Embed(title=_title, color=7506394, url="https://dis.gd/jobs")
            emb.description = await self.bot._(ctx.channel, "fun", "discordjobs-count", c=len(f_jobs))
            for i in range(0, len(f_jobs), 10):
                   emb.add_field(name="​", value="\n".join(f_jobs[i:i+10]))
            await ctx.send(embed=emb)
        else:
            await ctx.send("\n".join(f_jobs[:20]))
    

    @commands.command(name="discordstatus", aliases=['discord_status', 'status.gg'])
    @commands.cooldown(2, 60, commands.BucketType.channel)
    async def discordstatus(self, ctx: MyContext):
        """Know if Discord currently has a technical issue"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discordstatus.com/api/v2/incidents.json") as r:
                data = await r.json()
        last_incident = data['incidents'][0]
        if last_incident['resolved_at'] is None:
            impact = await self.bot._(ctx.channel, "fun", "discordstatus-impacts")
            impact = impact.get(last_incident['impact'])
            title = f"[{last_incident['name']}]({last_incident['shortlink']})"
            await ctx.send(await self.bot._(ctx.channel, "fun", "discordstatus-exists", impact=impact, title=title))
        else:
            last_date = datetime.datetime.strptime(last_incident['resolved_at'], '%Y-%m-%dT%H:%M:%S.%f%z')
            _lang = await self.bot._(ctx.channel,'current_lang','current')
            last_date = await self.bot.get_cog("TimeUtils").date(last_date, _lang, timezone=True)
            await ctx.send(await self.bot._(ctx.channel, "fun", "discordstatus-nothing", date=last_date))
        

    @commands.command(name="vote")
    @commands.cooldown(4, 30, type=commands.BucketType.guild)
    async def vote(self,ctx: MyContext,number:typing.Optional[int] = 0,*,text):
        """Send a message on which anyone can vote through reactions. 
        A big thank to Adri for his emojis specially designed for the bot!
        
        If no number of choices is given, the emojis will be 👍 and 👎. Otherwise, it will be a series of numbers.
        The text sent by the bot is EXACTLY the one you give, without any more formatting.
        
        ..Example vote Do you like axolotl?
        
        ..Example 3 Do you prefer blue, red or green? Answer below!
        
        ..Doc miscellaneous.html#vote"""
        text = await ctx.bot.get_cog('Utilities').clear_msg(text,ctx=ctx)
        if ctx.guild is not None:
            if not (ctx.channel.permissions_for(ctx.guild.me).read_message_history and ctx.channel.permissions_for(ctx.guild.me).add_reactions):
                return await ctx.send(await self.bot._(ctx.channel,"fun","cant-react"))
        if number == 0:
            m = await ctx.send(text)
            try:
                await self.add_vote(m)
            except Exception as e:
                await ctx.send(await self.bot._(ctx.channel,"fun","no-reaction"))
                await self.bot.get_cog("Errors").on_error(e, ctx)
                return
        else:
            if ctx.bot_permissions.external_emojis:
                emojis = self.bot.get_cog('Emojis').numbEmojis
            else:
                emojis = [chr(48+i)+chr(8419) for i in range(10)]
            if number>20 or number < 0:
                await ctx.send(await self.bot._(ctx.channel,"fun","vote-0"))
                return
            m = await ctx.send(text)
            for x in range(1,number+1):
                try:
                    await m.add_reaction(emojis[x])
                except discord.errors.NotFound:
                    return
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,ctx)
        await self.bot.get_cog('Utilities').suppr(ctx.message)
        self.bot.log.debug(await self.bot.get_cog('TimeUtils').date(datetime.datetime.now(),digital=True)+" Vote de {} : {}".format(ctx.author,ctx.message.content))


    async def check_suggestion(self,message):
        if message.guild is None or not self.bot.is_ready() or not self.bot.database_online:
            return
        try:
            channels = await self.bot.get_config(message.guild.id,'poll_channels')
            if channels is None or len(channels) == 0:
                return
            if str(message.channel.id) in channels.split(';') and not message.author.bot:
                try:
                    await self.add_vote(message)
                except:
                    pass
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,message)

def setup(bot):
    bot.add_cog(Fun(bot))
