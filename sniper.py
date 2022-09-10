# import everything we need to snipe
from msmcauth import login
from threading import Thread
from datetime import datetime
from colored import fore, style
from time import perf_counter, time, sleep
from discord_webhook import DiscordEmbed, DiscordWebhook
import asyncio, platform, re, socket, ssl, urllib.parse, requests, os, json, base64

# all sniping utilities
class Tools:
    # console logging/prefix function
    def new_prefix(color = fore.SKY_BLUE_2): 
        return f'{style.DIM}[{str(datetime.now()).split(".")[0].split(" ")[-1]}{style.RESET} {color}{SNIPER_NAME}{fore.WHITE}{style.DIM}]{style.RESET}{fore.WHITE}'

    # check if mc username is valid
    def username_valid(test_str):
        return len(test_str) >= 3 and len(test_str) <= 16 and not re.search(r'[^\.a-zA-Z0-9_]', test_str)

    # star.shopping droptime api function
    def get_droptime(username):
        try:
            droptime = int(requests.get(f"http://api.star.shopping/droptime/{username}", headers={"User-Agent": "Sniper"}).json()['unix'])
            print(f'{Tools.new_prefix(fore.BLUE)} Received droptime of "{username}" from api.star.shopping! UNIX: {droptime}')
        except:
            print(f'{Tools.new_prefix(fore.YELLOW_1)} Failed getting droptime of "{username}" from api.star.shopping!')
            droptime = int(input(f'{Tools.new_prefix(fore.RED)} Enter Manual Droptime! UNIX >:'))
            print(f'{Tools.new_prefix(fore.YELLOW_1)} Set Droptime: {datetime.utcfromtimestamp(droptime).strftime("%I:%M:%S.%f")}')
        return droptime

    # microsoft auth function w/ manual bearer
    def ms_authorize():
        valid = False; tokens = []

        for i in range (len(open("accounts.txt", "r").read().splitlines())):
            for _ in range(1):
                try:
                    account = open("accounts.txt", "r").read().splitlines()
                    accountsplit = re.split(f':|\n', account[i])

                    if accountsplit[0] == 'bearer':
                        try:
                            if json.loads(base64.b64decode(accountsplit[1].split('.')[1] + '=='))['exp'] < time():
                                print(f"{Tools.new_prefix(fore.RED)} '{accountsplit[1][0:12]}' has expired! ;(                                                 ")
                                return None
                        except:
                            print(f"{Tools.new_prefix(fore.RED)} '{accountsplit[1][0:12]}' is invalid!                                                    ")
                            return None

                        tokens.append(f"{accountsplit[1]}[]{accountsplit}")
                        print(f"{Tools.new_prefix(fore.GREEN)} Successfully logged in with bearer token!                          ")
                        valid = True
                        break
                    
                    sleep(25)

                    resp = login(accountsplit[0], accountsplit[1])
                    
                    tokens.append(f"{resp.access_token}[]{accountsplit}")
                    print(f"{Tools.new_prefix(fore.GREEN)} Successfully logged into '{accountsplit[0]}'!                          ")
                    valid = True
                    break

                except:
                    print(f"{Tools.new_prefix(fore.RED)} '{accountsplit[0]}' failed to login!                          ")
                    pass
        
        if valid != True:
            print(f"{Tools.new_prefix(fore.YELLOW)} Unable to find a usable account!")

        return tokens

    # detection successful account
    def detect_success(target, tokens):
        global successtoken, successcombo

        # try this 3 times
        for i in range(3):
            for i in range(len(tokens)):
                try: # check if token has target username
                    if requests.get("https://api.minecraftservices.com/minecraft/profile", headers={"Authorization": f"Bearer {tokens[i].split('[]')[0]}"}).json()['name'] == target:
                        successcombo = tokens[i].split('[]')[1]
                        successtoken = tokens[i].split('[]')[0]
                        break
                except: pass
                sleep(0.1)

            try: accs = open("success.txt", "a")
            except FileNotFoundError: accs = open("success.txt", "+w")

            try:
                accs.write(f"{successcombo} ~ {target}\n")
                accs.close()
                return successtoken
            except:
                print(f"\n{Tools.new_prefix(fore.YELLOW)} Success detection failed! >:( Retrying...", end='\r')
                sleep(5)

        print(f'{Tools.new_prefix(fore.YELLOW)} Unable to find the successful account ;-;')
        return None

    # announce successful snipe
    def announce_snipe(target):
        global announce_webhook
        if announce_webhook != None:
            try:
                DiscordWebhook(
                    content = f'🔫 `{target}`',
                    username = SNIPER_NAME,
                    url = announce_webhook, 
                    rate_limit_retry = True
                ).execute()
                print(f'{Tools.new_prefix(fore.GREEN)} Announced to Discord Webhook!')
            except:print(f'{Tools.new_prefix(fore.RED)} Failed to announce to webhook.')

# network sniping utilities
class Sniper:
    # get ping to the minecraft API
    async def get_ping():
        pingtimes = []

        for _ in range(3):
            uri = urllib.parse.urlparse("https://api.minecraftservices.com/minecraft")
            reader, writer = await asyncio.open_connection(uri.hostname, 443, ssl=False)
            writer.write(f"GET {uri.path or '/'} HTTP/1.1\r\nHost:{uri.hostname}\r\n\r\n".encode())

            await writer.drain(); start     = perf_counter()
            await reader.read(1); end       = perf_counter()

            pingtimes.append(end-start)

        return sum(pingtimes) / len(pingtimes) * 1000

    # main request sending
    def send_request(target, payload, sendTime, droptime, tokenNumber):
        global prints, data, successTokenNumber

        try:sleep(sendTime - time() - 5)
        except:pass
        
        # connect to the api
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((MC_API, 443))
            with ssl.create_default_context().wrap_socket(s, server_hostname='api.minecraftservices.com') as mainsocket:
                # wait until send time
                sleep(sendTime - time() - 1)                
                while time() < sendTime:pass

                # send request payload
                mainsocket.send(payload)
                send = time()
                sends.append(send)

                # receive all data
                reqData = mainsocket.recv(2048)
                recv    = time()
                
                # parse data
                recvs.append(recv)
                reqData = reqData.decode('utf-8')
                data.append(reqData)

        # semi-accurate early/late/close detection
        if recv - droptime < 0.01:                              timing = f'Early by {round((recv - droptime - 0.01)*10000)/10}ms'
        elif recv - droptime > 0.02:                            timing = f'Late by {round((recv - droptime - 0.02)*10000)/10}ms'
        elif recv - droptime < 0.02 and recv - droptime > 0.01: timing = 'Was close :o'
        if int(reqData[9:12]) == 429:                           timing = 'Was ratelimited :('
        elif int(reqData[9:12]) == 200:                         timing = 'Hit :]'
        elif '50' in str(reqData[9:12]):                        timing = 'Lagged >:('

        print(f"{Tools.new_prefix(fore.GREEN)} {datetime.utcfromtimestamp(send).strftime('%S.%f')} -> {datetime.utcfromtimestamp(recv).strftime('%S.%f')} | [{str(reqData[9:12])}] {timing}")
        
        # detect success
        logChar = '-'
        if int(reqData[9:12]) == 200:
            successTokenNumber = tokenNumber
            logChar = '+'

        prints.append(f'{logChar} {datetime.utcfromtimestamp(send).strftime("%S.%f")} -> {datetime.utcfromtimestamp(recv).strftime("%S.%f")} | {str(reqData[9:12])} {timing}')

# global variables
VERSION     = '1.0.0_beta001'
MC_API      = 'api.minecraftservices.com'
SNIPER_NAME = 'fapps'
CONFIG_FILE = 'fapps.json'

# dynamic delay calculation
async def delay_calculation(ping, type):
    # CHANGE CALCULATION HERE

    if type == 'nc': # default is ping times .9 then add 16
        return (ping * 0.9) + 16

    if type == 'gc': # default is ping times 1.35 then add 13.5
        return (ping * 1.35) + 13.5

# Windows only asyncio fix
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# clear terminal, platform specific using Ternary operator :)
os.system("cls") if platform.system() == 'Windows' else os.system("clear")
   
# print out Sniper logo
print(f'\n        {fore.ORANGE_1}      ____                      ')
print(f'             / __/___ _____  ____  _____')
print(f'            / /_/ __ `/ __ \/ __ \/ ___/')
print(f'           / __/ /_/ / /_/ / /_/ (__  ) ')
print(f'          /_/  \__,_/ .___/ .___/____/  ')
print(f'                   /_/   /_/            ')
print(f'\n              {fore.WHITE}{style.UNDERLINED}Version{style.RESET}{fore.WHITE}: {fore.RED}{VERSION}{fore.WHITE}\n\n')

# check if our fapps.json config file is present
if not os.path.isfile(CONFIG_FILE): 
    quit(input(f'{Tools.new_prefix(fore.YELLOW_1)} Please create a "{CONFIG_FILE}" and retry!\n{Tools.new_prefix(fore.YELLOW_1)} Press ENTER to exit...'))

# set snipe configuration using loaded config file
global nc_request_amount, gc_request_amount, announce_webhook, private_log_webhook
try:
    config                  = json.loads(open(CONFIG_FILE).read())
    nc_request_amount       = config['nc_request_amount']
    gc_request_amount       = config['gc_request_amount']
    announce_webhook        = config['webhook_url']
    private_log_webhook     = config['webhook_for_times']
except Exception as ex:
    print(f'{Tools.new_prefix(fore.YELLOW_1)} Failed to load config file! Error: {ex}')
    nc_request_amount       = 3
    gc_request_amount       = 2
    announce_webhook        = None
    private_log_webhook     = None

# get sniping type
snipingType = input(f'{Tools.new_prefix(fore.BLUE)} Enter Snipe Type! (gc/nc) >:').lower()
if snipingType != 'gc' and snipingType != 'nc':
    quit(input(f'{Tools.new_prefix(fore.RED)} The type entered was invalid! Press ENTER to exit...'))

# get target username
target = input(f'{Tools.new_prefix(fore.BLUE)} Enter Target! >:')
if not Tools.username_valid(target):
    quit(input(f'{Tools.new_prefix(fore.RED)} The username entered was invalid! Press ENTER to exit...'))

# get droptime & offset
droptime     = Tools.get_droptime(target)
offset       = input(f'{Tools.new_prefix(fore.BLUE)} Enter Offset! >:')

while True:
    try:test = open('accounts.txt', "r"); test.close(); break
    except:input(f"{Tools.new_prefix(fore.RED)} Please create accounts.txt!\n{Tools.new_prefix(fore.YELLOW)} Press ENTER once complete...\n")


while droptime > time() + (len(open("accounts.txt", "r").read().splitlines())*25) + 75:
    sleep(0.1); print(f"{Tools.new_prefix(fore.ORANGE_1)} Sniping '{target}' in {datetime.utcfromtimestamp(int(droptime) - time()).strftime('%H:%M:%S')}                        ", end='\r')

print(f"{Tools.new_prefix(fore.YELLOW)} Starting authentication for '{target}'...                        ")
bearers = Tools.ms_authorize() 
print(f"{Tools.new_prefix(fore.GREEN)} Locked and loaded! Good luck <3\n")

success = False

global data, prints, sends, recvs, request_times
data            = []
prints          = []
sends           = []
recvs           = []
payloads        = []
threads         = []
request_times   = []

aL = asyncio.new_event_loop()
currentPing = aL.run_until_complete(Sniper.get_ping())
possibleCalc = float(aL.run_until_complete(delay_calculation(currentPing, snipingType)))    
if possibleCalc != 0 and offset == 'calc':
    print(f'{Tools.new_prefix(fore.ORANGE_1)} Calculated Offset: {round(possibleCalc*10)/10} ~ Ping: {round(currentPing*10)/10}'); offset = float(possibleCalc)
else:
    offset = float(offset)

if snipingType == 'nc':
    payloads = [f'PUT /minecraft/profile/name/{target} HTTP/1.1\r\nHost: api.minecraftservices.com\r\nAuthorization: Bearer {i.split("[]")[0]}\r\n\r\n'.encode('utf-8') for i in bearers]
elif snipingType == 'gc':
    payloads = [bytes("\r\n".join(["POST /minecraft/profile HTTP/1.1", "Host: api.minecraftservices.com", "Content-Type: application/json", f"Authorization: Bearer {i.split('[]')[0]}", "User-Agent: fapps", "Content-Length: %d" % len('{"profileName": "%s"}' % target), "", '{"profileName": "%s"}' % target]), "utf-8") for i in bearers]
    
for x in range(len(payloads)):
    if snipingType == 'nc':
        for _ in range(nc_request_amount):
            threads.append(Thread(target=Sniper.send_request, args=(target, payloads[x], (droptime-(offset/1000)), droptime, x)))
    elif snipingType == 'gc':
        for _ in range(gc_request_amount):
            threads.append(Thread(target=Sniper.send_request, args=(target, payloads[x], (droptime-(offset/1000)), droptime, x)))

for t in threads:t.start()
if (droptime - time()) > 0: sleep(droptime - time())
for t in threads:t.join()

try:print(f"\n{Tools.new_prefix(fore.BLUE)} Sent w/ ~{0 - (round(len(sends) / ((sends[0] - sends[len(sends) - 1])) / 1000))} r/ms                          ")
except:print(f"\n{Tools.new_prefix(fore.BLUE)} Sent w/ ~infinite? r/ms (Windows Error)                          ")

try:
    logfile = open(f'logs/{target}.txt', '+w', encoding='utf-8')
except:
    os.mkdir('logs')
    logfile = open(f'logs/{target}.txt', '+w', encoding='utf-8')

logfile.write(f'Offset: {offset}\n\n'+'\n'.join(prints)); logfile.close()

try:
    loop = asyncio.new_event_loop()
    ping = loop.run_until_complete(Sniper.get_ping())
    if private_log_webhook != None:
        DiscordWebhook(rate_limit_retry=True, url=private_log_webhook, content=f"Target Username :white_small_square: : `{target}`\nCurrent Ping :white_small_square: : `{ping}`\nUsed Offset :white_small_square: : `{offset}`\nSniper Type :white_small_square: : `Namechange`\nTimes Below :white_small_square: :\n" + '```diff\n' + ('\n').join(prints) + '```').execute()
    print(f"{Tools.new_prefix(fore.GREEN)} Successfully logged times to private webhook ;D")
except:
    print(f"{Tools.new_prefix(fore.RED)} Failed to log times to private webhook :c")

# detect a successful response
for i in data: 
    if int(i[9:12]) < 400: 
        success = True

# finish up everything & logh out if sniped
if success == True:
    print(f"{Tools.new_prefix(fore.GREEN)} Successfully sniped '{target}'! ;)                          ")
    Tools.detect_success(target=target, tokens=bearers)
    print(f'{Tools.new_prefix(fore.BLUE)} Skinchange: {requests.post("https://api.minecraftservices.com/minecraft/profile/skins", headers={"Authorization": f"Bearer {successtoken}", "Content-Type": "application/json"}, json={"url": "https://textures.minecraft.net/texture/54a4a0a20cf1a74a5a4e626c8856bdfb2ab5ee7596a9828eb97638d84ec4c4bd", "variant": "classic"}).status_code}')
    Tools.announce_snipe(target=target) 
elif success == False:
    print(f"{Tools.new_prefix(fore.RED)} Failed to snipe '{target}'!                          ")

quit(input(f'{Tools.new_prefix(fore.ORANGE_1)} Sniping done! Press ENTER to exit...'))