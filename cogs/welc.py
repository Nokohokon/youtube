import discord
from discord.ext import commands
import ezcord
from backend import welc

class Welc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        welc_channel = welc.get_welc(member.guild.id)
        welc_message = welc.get_welc_message(member.guild.id)
        if welc_channel:
            channel = member.guild.get_channel(welc_channel)
            if welc_message:
                await channel.send(welc_message)
            else:
                await channel.send(f"Willkommen {member.mention}")
        else:
            await member.send(f"Willkommen auf {member.guild.name}! Bitte beachte die Regeln und viel Spaß!")


def setup(bot):
    bot.add_cog(Welc(bot))
