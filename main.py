# version 1.1.3

import discord
from discord.ext import commands, tasks
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

# Timestamp of last schedule (the starttime of onwarding one)
last_schedule_timestamp = 0
# A dict save the map info retrieved from url.
schedule = None
# Alarm happen when True. This is set to True when schedule updated successfully.
alarm_trigger = False
# A flag to ignore the first schedule update (schedule init) in alarm loop.
schedule_first_check = True
# Some funny quotes added in alarm.
alarm_quote = ['趕快來打真劍吧!', '快來爬管吧!', '是不是要上X了!', '該來打了吧?', '很期待你直播欸!', '上X就是今天了', '上X的機會，走過路過千萬別錯過!']

# schedule update handler
def check_schedule_update():
    global last_schedule_timestamp, alarm_trigger, schedule_first_check
    current_timestamp = int(datetime.datetime.now().timestamp())

    if math.floor(last_schedule_timestamp/7200) < math.floor(current_timestamp/7200):
        global schedule
        url = requests.get(setting['schedule_url'])
        schedule = json.loads(url.text)
        last_schedule_timestamp = schedule['modes']['regular'][0]['startTime']
        write_log(' - a GET request is called to retrieve the schedule.')
        write_log(f'   - Schedule TimeStamp: {last_schedule_timestamp}')
        alarm_trigger = True
    
    if schedule_first_check == True:
        schedule_first_check = False
        return True
    else:
        return False

# Translate user-named map into standard map name
def get_map_name(m):
    if m in find_map:
        return find_map[m]
    else:
        return '.'

# User data saving handler
def save_user_data():
    with open('json/user_data.json', mode = 'w', encoding = 'utf8') as jdata:
        json.dump(user_data, jdata)

# log
def write_log(content):
    f = open('log.txt', 'a')
    time = datetime.datetime.fromtimestamp(datetime.datetime.now().timestamp() + setting['timezone_delta'])
    f.write(f'{time.strftime("%Y/%m/%d %H:%M")}: {content}\n')
    f.close()
    print(content)


intents = discord.Intents.default()
splatbot = commands.Bot(command_prefix = '$',intents = intents)

# Init setup
@splatbot.event
async def on_ready():
    write_log('--- We have logged in as {0.user} ---'.format(splatbot))
    check_schedule_update()
    global alarm_trigger
    alarm_trigger = False
    gachi_alarm.start()

# Chinese help
@splatbot.command(name='說明')
async def usage(ctx):
    await ctx.send(
        '```$場地 : 顯示現在以及下一次的場地 \n' \
        + '$新增 : 新增喜愛的場地 \n' \
        + ' - 用法 : $新增 [場地1] [場地2] [場地3]... \n' \
        + '$移除 : 移除喜愛的場地 \n' \
        + ' - 用法 : $移除 [場地1] [場地2] [場地3]... \n' \
        + '$討厭 : 新增討厭的場地 \n' \
        + ' - 用法 : $喜歡 [場地1] [場地2] [場地3]... \n' \
        + '$不討厭 : 移除討厭的場地 \n' \
        + ' - 用法 : $不討厭 [場地1] [場地2] [場地3]... \n' \
        + '$喜愛 : 顯示目前的個人設定 \n' \
        + '$時間 : 設定小管家只提醒特定時段 \n' \
        + ' - 用法 : $時間 [開始時間] [結束時間] / $時間 重設 \n' \
        + '\n' \
        + 'SplatBot會在您喜歡的場地出現在真劍時通知您，必要時也會情勒您。```' \
    )

# Show current and next map schedule
@splatbot.command(name='場地')
async def map_info(ctx):

    check_schedule_update()

    for i in [0, 1]:
        starttime = datetime.datetime.fromtimestamp(schedule['modes']['regular'][i]['startTime'] + setting['timezone_delta'])
        endtime = datetime.datetime.fromtimestamp(schedule['modes']['regular'][i]['endTime'] + setting['timezone_delta'])
        
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

# Add liked map for a user
@splatbot.command(name='新增')
async def add_liked_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $新增 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        elif (user_data[user_id]['likedmap'] & map_enum[map_name]) > 0:
            bot_message += f'{ch_name[map_name]} 已經是喜愛的場地了 \n'
        else:
            user_data[user_id]['likedmap'] += map_enum[map_name]
            write_log(f' - "{ctx.author.name}" added "{map_name}({ch_name[map_name]})" to liked map')
            bot_message += f'新增喜愛的場地 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# Remove liked map for a user
@splatbot.command(name='移除')
async def rm_liked_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $移除 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        elif (user_data[user_id]['likedmap'] & map_enum[map_name]) == 0:
            bot_message += f'{ch_name[map_name]} 不是喜愛的場地 \n'
        else:
            user_data[user_id]['likedmap'] -= map_enum[map_name]
            write_log(f' - "{ctx.author.name}" removed "{map_name}({ch_name[map_name]})" from liked map')
            bot_message += f'從喜愛的場地中移除 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# Add rejected map for a user
@splatbot.command(name='討厭')
async def add_rejected_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $討厭 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        elif (user_data[user_id]['rejectedmap'] & map_enum[map_name]) > 0:
            bot_message += f'{ch_name[map_name]} 已經被你討厭了! \n'
        else:
            user_data[user_id]['rejectedmap'] += map_enum[map_name]
            write_log(f' - "{ctx.author.name}" added "{map_name}({ch_name[map_name]})" to rejected map')
            bot_message += f'新增討厭的場地 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# Remove rejected map for a user
@splatbot.command(name='不討厭')
async def rm_rejected_map(ctx, *args):
    user_id = str(ctx.author.id)
    
    if len(args) == 0:
        await ctx.reply('用法: $不討厭 *[場地1] [場地2] [場地3]*...')
        return
        
    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
    
    bot_message = ''
    for pre_map_name in args:
        map_name = get_map_name(pre_map_name)

        if map_name not in map_enum:
            bot_message += f'找不到場地名稱或編號 "{pre_map_name}" \n'
        
        elif (user_data[user_id]['rejectedmap'] & map_enum[map_name]) == 0:
            bot_message += f'{ch_name[map_name]} 不是討厭的場地 \n'
        else:
            user_data[user_id]['rejectedmap'] -= map_enum[map_name]
            write_log(f' - "{ctx.author.name}" removed "{map_name}({ch_name[map_name]})" from rejected map')
            bot_message += f'從討厭的場地中移除 {ch_name[map_name]} \n'

    await ctx.reply(bot_message)
    save_user_data()

# Set alarm time for a user
@splatbot.command(name='時間')
async def set_alarm_time(ctx, *args):
    user_id = str(ctx.author.id)
    
    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
    
    bot_message = ''

    if len(args) == 0:
        bot_message += '用法: $時間 *[開始時間] [結束時間]*\n或是\n$時間 重設'

    elif len(args) == 1:
        if args[0] == '重設':
            user_data[user_id]['starttime'] = 0
            user_data[user_id]['endtime'] = 24
            bot_message += '已將提醒時間設為 任何時刻'
        else:
            bot_message += '用法: $時間 *[開始時間] [結束時間]*\n或是\n$時間 重設'

    else:
        if args[0].isnumeric() and args[1].isnumeric():
            if 0 <= int(args[0]) <= 24 and 0 <= int(args[1]) <= 24:
                user_data[user_id]['starttime'] = int(args[0])
                user_data[user_id]['endtime'] = int(args[1])
                bot_message += f'已將提醒時間設為{int(args[0])}時至{int(args[1])}時' if int(args[0]) <= int(args[1]) else f'已將提醒時間設為{int(args[0])}時至隔日{int(args[1])}時'
            else:
                bot_message += '時間需介於0時至24時之間'
                
        else:
            bot_message += '時間請輸入數字'
        

    await ctx.reply(bot_message)
    save_user_data()

# Display user's liked map and rejected map
@splatbot.command(name='喜愛')
async def show_liked_map(ctx):
    user_id = str(ctx.author.id)
    bot_message = ''

    if user_id not in user_data:
        user_data[user_id] = setting['user_data_default']
        save_user_data()
    
    if user_data[user_id]['likedmap'] == 0:
        bot_message += '目前沒有喜愛的場地'
    else:
        bot_message += '目前喜愛的場地 : \n'
        for i in range(23):
            if (user_data[user_id]['likedmap'] & 2**i) > 0:
                bot_message += ch_name[get_map_name(str(i+1))] + ' \n'
    
    if user_data[user_id]['rejectedmap'] == 0:
        bot_message += '目前沒有討厭的場地'
    else:
        bot_message += '目前討厭的場地 : \n'
        for i in range(23):
            if (user_data[user_id]['rejectedmap'] & 2**i) > 0:
                bot_message += ch_name[get_map_name(str(i+1))] + ' \n'

    if user_data[user_id]['starttime'] <= user_data[user_id]['endtime']:
        bot_message += f'目前設定的時間 : {user_data[user_id]["starttime"]}時至{user_data[user_id]["endtime"]}時'
    else:
        bot_message += f'目前設定的時間 : {user_data[user_id]["starttime"]}時至隔日{user_data[user_id]["endtime"]}時'

    await ctx.reply(bot_message)

@splatbot.command()
@commands.is_owner()
async def reload_json(ctx):
    global setting, ch_name, map_enum, find_map, user_data
    with open('json/bot_setting.json', mode = 'r', encoding = 'utf8') as jfile1, \
     open('json/ch_name.json', mode = 'r', encoding = 'utf8') as jfile2, \
     open('json/map_enum.json', mode = 'r', encoding = 'utf8') as jfile3, \
     open('json/find_map.json', mode = 'r', encoding = 'utf8') as jfile4:
        setting, ch_name, map_enum, find_map = json.load(jfile1), json.load(jfile2), json.load(jfile3), json.load(jfile4)
    with open('json/user_data.json', mode = 'r', encoding = 'utf8') as jdata:
        user_data = json.load(jdata)

@splatbot.command()
@commands.is_owner()
async def reload_ext(ctx):
    splatbot.unload_extension('ext.debug_command')
    splatbot.load_extension('ext.debug_command')

# Gachi alarm loop
@tasks.loop(minutes = 5)
async def gachi_alarm():
    
    await splatbot.wait_until_ready()
    global alarm_trigger
    
    check_schedule_update()

    if alarm_trigger == False:
        return
    alarm_trigger = False

    write_log(' - Executing alarm process...')

    maps_gachi1 = schedule['modes']['gachi'][1]['maps'][0]
    maps_gachi2 = schedule['modes']['gachi'][1]['maps'][1]
    rule_gachi = schedule['modes']['gachi'][1]['rule']['name']
    time_gachi = datetime.datetime.fromtimestamp(schedule['modes']['gachi'][1]['startTime'] + setting['timezone_delta'])
    alarm_channel = splatbot.get_channel(setting['alarm_channel_id'])

    bot_message = ''

    for user_id in user_data:
        if user_data[user_id]['rejected'] & map_enum[maps_gachi1] > 0 \
        or user_data[user_id]['rejected'] & map_enum[maps_gachi2] > 0:
            continue

        if user_data[user_id]['likedmap'] & map_enum[maps_gachi1] > 0 \
        or user_data[user_id]['likedmap'] & map_enum[maps_gachi2] > 0:

            starttime, endtime = user_data[user_id]['starttime'], user_data[user_id]['endtime']
            currenttime = time_gachi.hour
            if (starttime <= endtime and (starttime <= currenttime + 1 and currenttime + 1 <= endtime)) \
            or (starttime > endtime and (starttime <= currenttime + 1 or  currenttime + 1 <= endtime)):
                user = await splatbot.fetch_user(int(user_id))
                bot_message += f'{user.mention} '
            
    if bot_message != '':
        filename1 = 'images/' + maps_gachi1.replace(' ', '') + '.png'
        filename2 = 'images/' + maps_gachi2.replace(' ', '') + '.png'
        image1 = discord.File(filename1)
        image2 = discord.File(filename2)
        quote = random.choice(alarm_quote)
        bot_message += f'\n{time_gachi.strftime("%Y/%m/%d %H:%M")}是{ch_name[rule_gachi]}，場地不錯喔!{quote}'
        await alarm_channel.send(bot_message)
        await alarm_channel.send(files=[image1, image2])
        write_log('   - Some receive the alarm.')
    else :
        write_log('   - Nobody receives the alarm.')


if __name__ == '__main__':
    splatbot.load_extension('ext.debug_command')
    splatbot.run(setting['TOKEN'])
