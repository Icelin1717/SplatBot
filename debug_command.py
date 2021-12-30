import discord
from discord.ext import commands
import requests, json

class Debug_Command(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

        with open('json/bot_setting.json', mode = 'r', encoding = 'utf8') as jfile1, \
            open('json/ch_name.json', mode = 'r', encoding = 'utf8') as jfile2, \
            open('json/map_enum.json', mode = 'r', encoding = 'utf8') as jfile3, \
            open('json/find_map.json', mode = 'r', encoding = 'utf8') as jfile4:
            self.setting = json.load(jfile1)
            self.ch_name = json.load(jfile2)
            self.map_enum = json.load(jfile3)
            self.find_map = json.load(jfile4)

    @commands.command()
    async def alarm_test(self, ctx):
        alarm_channel = self.bot.get_channel(self.setting['alarm_channel_id'])
        await alarm_channel.send('DEBUG: This message should be displayed in alarm channel.')
