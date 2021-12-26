# version 1.0.1

import discord
from discord.ext import commands, tasks
from debug_command import Debug_Command
import requests
import json
import datetime
import math
import random


# * load essential json file
with open('json/bot_setting.json', mode = 'r', encoding = 'utf8') as jfile1, \
     open('json/ch_name.json', mode = 'r', encoding = 'utf8') as jfile2, \
     open('json/map_enum.json', mode = 'r', encoding = 'utf8') as jfile3, \
     open('json/find_map.json', mode = 'r', encoding = 'utf8') as jfile4:
    setting, ch_name, map_enum, find_map = json.load(jfile1), json.load(jfile2), json.load(jfile3), json.load(jfile4)

# * load user data
with open('json/user_data.json', mode = 'r', encoding = 'utf8') as jdata:
    user_data = json.load(jdata)

# * function and variable

last_schedule_timestamp = None
first_loop_flag = True
schedule = None
alarm_trigger = False
alarm_quote = ['趕快來打真劍吧!', '快來爬管吧!', '是不是要上X了!', '該來打了吧?', '很期待你直播欸!']

def check_schedule_update():
    global last_schedule_timestamp, alarm_trigger
    current_timestamp = int(datetime.datetime.now().timestamp())

    if last_schedule_timestamp == None or math.floor(last_schedule_timestamp/7200) < math.floor(current_timestamp/7200):
        global schedule
        url = requests.get(setting['schedule_url'])
        schedule = json.loads(url.text)
        last_schedule_timestamp = schedule['modes']['regular'][0]['startTime']
        print(' - a GET request is called to retrieve the schedule')
        alarm_trigger = True
    else:
        alarm_trigger = False

def get_map_name(m):
    if m in find_map:
        return find_map[m]
    else:
        return '.'

def save_user_data():
    with open('json/user_data.json', mode = 'w', encoding = 'utf8') as jdata:
        json.dump(user_data, jdata)

intents = discord.Intents.default()
splatbot = commands.Bot(command_prefix = '$',intents = intents)

# * init setup
@splatbot.event
async def on_ready():
    
    check_schedule_update()
    print('--- We have logged in as {0.user} ---'.format(splatbot))

# * chinese help
@splatbot.command(name='說明')
async def usage(ctx):
    await ctx.send(
        '```$場地 : 顯示現在以及下一次的場地 \n' \
        + '$新增 : 新增喜愛的場地 \n' \
        + ' - 用法 : $新增 [場地1] [場地2] [場地3]... \n' \
        + '$移除 : 移除喜愛的場地 \n' \
        + ' - 用法 : $移除 [場地1] [場地2] [場地3]... \n' \
        + '$喜愛 : 顯示目前喜愛的場地列表 \n' \
        + '\n' \
        + 'SplatBot會在您喜歡的場地出現在真劍時通知您，必要時也會情勒您。```' \
    )

# * show current and next map schedule
@splatbot.command(name='場地')
async def info(ctx):

    check_schedule_update()

    for i in [0, 1]:
        starttime = datetime.datetime.fromtimestamp(schedule['modes']['regular'][i]['startTime'])
        endtime = datetime.datetime.fromtimestamp(schedule['modes']['regular'][i]['endTime'])
        
        maps_regular = schedule['modes']['regular'][i]['maps']
        maps_gachi = schedule['modes']['gachi'][i]['maps']
        rule_gachi = schedule['modes']['gachi'][i]['rule']['name']
        maps_league = schedule['modes']['league'][i]['maps']
        rule_league = schedule['modes']['league'][i]['rule']['name']

        timerange_str = f'{starttime.strftime("%Y/%m/%d %H:%M")} ~ {endtime.strftime("%Y/%m/%d %H:%M")} \n'
        regular_str = f'塗地 : {ch_name[maps_regular[0]]}, {ch_name[maps_regular[1]]} \n'
        gachi_str = f'真劍 : {ch_name[maps_gachi[0]]}, {ch_name[maps_gachi[1]]}   (模式 : {ch_name[rule_gachi]}) \n'
        league_str = f'聯盟 : {ch_name[maps_league[0]]}, {ch_name[maps_league[1]]}   (模式 : {ch_name[rule_league]})'

        await ctx.send(timerange_str + regular_str + gachi_str + league_str)

# * add liked map for a user
@splatbot.command(name='新增')
async def add_liked_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $新增 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = {'likedmap': 0, 'starttime': 0, 'endtime': 24}
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        if (user_data[user_id]['likedmap'] & map_enum[map_name]) > 0:
            bot_message += f'{ch_name[map_name]} 已經是喜愛的場地了 \n'
        else:
            user_data[user_id]['likedmap'] += map_enum[map_name]
            print(f' - "{ctx.author.name}" added "{map_name}({ch_name[map_name]})" to liked map')
            bot_message += f'新增喜愛的場地 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# * remove liked map for a user
@splatbot.command(name='移除')
async def rm_liked_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $移除 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = {'likedmap': 0, 'starttime': 0, 'endtime': 24}
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        if (user_data[user_id]['likedmap'] & map_enum[map_name]) == 0:
            bot_message += f'{ch_name[map_name]} 不是喜愛的場地 \n'
        else:
            user_data[user_id]['likedmap'] -= map_enum[map_name]
            print(f' - "{ctx.author.name}" removed "{map_name}({ch_name[map_name]})" from liked map')
            bot_message += f'從喜愛的場地中移除 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# * display user's liked map
@splatbot.command(name='喜愛')
async def show_liked_map(ctx):
    user_id = str(ctx.author.id)

    if user_id not in user_data:
        user_data[user_id] = {'likedmap': 0, 'starttime': 0, 'endtime': 24}
        save_user_data()
    
    if user_data[user_id]['likedmap'] == 0:
        await ctx.reply('目前沒有喜愛的場地')
        return

    bot_message = '目前喜愛的場地 : \n'
    for i in range(23):
        if (user_data[user_id]['likedmap'] & 2**i) > 0:
            bot_message += ch_name[get_map_name(str(i+1))] + ' \n'
    await ctx.reply(bot_message)

# * alarm loop
@tasks.loop(minutes = 5)
async def game_alarm():
    
    await splatbot.wait_until_ready()
    global first_loop_flag, alarm_trigger
    
    check_schedule_update()

    if alarm_trigger == False:
        return
    elif first_loop_flag == True:
        first_loop_flag = False
        return
    alarm_trigger = False
    
    maps_gachi1 = schedule['modes']['gachi'][1]['maps'][0]
    maps_gachi2 = schedule['modes']['gachi'][1]['maps'][1]
    time_gachi = datetime.datetime.fromtimestamp(schedule['modes']['gachi'][1]['startTime'])
    alarm_channel = splatbot.get_channel(setting['alarm_channel_id'])
    image_flag = False  # whether show the map image

    bot_message = ''

    for user_id in user_data:
        if user_data[user_id]['likedmap'] & map_enum[maps_gachi1] > 0 \
        or user_data[user_id]['likedmap'] & map_enum[maps_gachi2] > 0:
            image_flag = True
            user = await splatbot.fetch_user(int(user_id))
            bot_message += f'{user.mention} '
            

    if image_flag:
        filename1 = 'images/' + maps_gachi1.replace(' ', '') + '.png'
        filename2 = 'images/' + maps_gachi2.replace(' ', '') + '.png'
        image1 = discord.File(filename1)
        image2 = discord.File(filename2)
        quote = random.choice(alarm_quote)
        bot_message += f'\n{time_gachi.strftime("%Y/%m/%d %H:%M")}的場地不錯喔!{quote}'
        await alarm_channel.send(bot_message)
        await alarm_channel.send(files=[image1, image2])

if __name__ == '__main__':
    splatbot.add_cog(Debug_Command(splatbot))
    game_alarm.start()
    splatbot.run(setting['TOKEN'])
