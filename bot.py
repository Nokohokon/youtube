import discord
import ezcord
from discord.ext.ipc import ClientPayload, Server


class Bot(ezcord.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)
        self.ipc = Server(self, secret_key="keks")

    async def on_ready(self):
        await self.ipc.start()
        print(f"{self.user} ist online")

    @Server.route()
    async def guild_count(self, _):
        return str(len(self.guilds))

    @Server.route()
    async def bot_guilds(self, _):
        guild_ids = [str(guild.id) for guild in self.guilds]
        return {"data": guild_ids}

    @Server.route()
    async def guild_stats(self, data: ClientPayload):
        guild = self.get_guild(data.guild_id)
        if not guild:
            return {
                "member_count": 69,
                "name": "Unbekannt"
            }

        return {
            "member_count": guild.member_count,
            "name": guild.name,
        }

    @Server.route()
    async def check_perms(self, data: ClientPayload):
        guild = self.get_guild(data.guild_id)
        if not guild:
            return {"perms": False}

        member = guild.get_member(int(data.user_id))
        if not member or not member.guild_permissions.administrator:
            return {"perms": False}

        return {"perms": True}
    
    @Server.route()
    async def get_guild_items(self,data: ClientPayload):
        guild = self.get_guild(data.guild_id)
        if not guild:
            return {
                "channels": [],
                "roles": [],
                "members": [],
            }
        return {
            "channels": [str(channel.id)+" " + channel.name for channel in guild.channels],
            "roles": [str(role.id) + " " + role.name for role in guild.roles],
            "members": [str(member.id) + " " + member.name for member in guild.members],
        }

    @Server.route()
    async def get_channel_name(self, data: ClientPayload):
        guild = self.get_guild(data.guild_id)
        channel = guild.get_channel(data.channel_id)
        return channel

    async def on_ipc_error(self, endpoint: str, exc: Exception) -> None:
        raise exc


bot = Bot()
bot.load_cogs(directory="cogs")
bot.run("TOKEN")