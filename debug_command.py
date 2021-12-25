import discord
from discord.ext import commands
import requests, json

class Debug_Command(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot;


    @commands.command()
    async def debug(self, ctx):
        await ctx.reply('This is a debug command\nhttps://twitter.com/SplatoonJP/status/1474303864828579850')

    @commands.command()
    async def info_origin(self, ctx):
        url = requests.get('https://splatoon.ink/schedule2.json')
        data = json.loads(url.text)

        maps_regular = data['modes']['regular'][0]['maps']
        maps_gachi = data['modes']['gachi'][0]['maps']
        rule_gachi = data['modes']['gachi'][0]['rule']['name']
        maps_league = data['modes']['league'][0]['maps']
        rule_league = data['modes']['league'][0]['rule']['name']

        await ctx.send(f'regular: {maps_regular} \n'
            + f'gachi: {maps_gachi} ( {rule_gachi} ) \n'
            + f'league: {maps_league} ( {rule_league} )')

    @commands.command()
    async def embedding(self, ctx):
        embed = discord.Embed(
            title = 'Maps',
            colour = discord.Colour.random()
        )
        embed.set_image(url = 'https://cdn.wikimg.net/en/splatoonwiki/images/thumb/c/c9/S2_Stage_Inkblot_Art_Academy.png/300px-S2_Stage_Inkblot_Art_Academy.png')

        await ctx.send(embed = embed)
