import configparser
import requests
import time
import os
import json
from discord import Webhook, RequestsWebhookAdapter
from PIL import Image


webhook = Webhook.from_url("https://discord.com/api/webhooks/929816118879739974/391qhpmd9xl71yLyM1bcLsi-94hFFFt6OtXWiO7tjbL_91N-ini_QFtG7FeR5rmO0o6R", adapter=RequestsWebhookAdapter())

pages = []
tradesToDecline = []
offers = []
c = requests.Session()
cachedProjs = []
itemChecked = []
winsSent = []
tradesChecked = {}
proxies={
        "http": "http://epkdhlyr-rotate:8vjn240pwn2j@p.webshare.io:80/",
        "https": "http://epkdhlyr-rotate:8vjn240pwn2j@p.webshare.io:80/"
    }

with open("tradesCached.json","r") as read_file:
    tradesChecked = json.load(read_file)
with open("winsSent.json", "r") as read_file:
    winsSent = json.load(read_file)['IDs']

print(tradesChecked)

config = configparser.ConfigParser()
config.read('config.ini')

try:
    g = config['Authentication']['roblosecurityCookie']
    loss = int(config['Settings']['lossThreshold'])
    win = int(config['Settings']['gainThreshold'])
    cooldown = int(config['Settings']['cooldownTime'])
    block = config['List']['itemsToAvoid'].split(",")
    ratio = float(config['Settings']['projectedVal'])
    keep = config['List']['itemsToKeep'].split(",")
    ignore = config['List']['itemsToIgnore'].split(",")
    speed = int(config['Settings']['requestsPerMin'])
    change = int(config['Settings']['changeThreshold'])
except:
    print("Does every value have the correct type of value?")
    time.sleep(30)
    os._exit(0)

for i in range(len(block)):
    block[i] = block[i].strip()
for i in range(len(keep)):
    keep[i] = keep[i].strip()
for i in range(len(ignore)):
    ignore[i] = ignore[i].strip()
if speed <= 0:
    print("Set your requestsPerMin higher than 0")
    time.sleep(30)
    os._exit(0)
cookies = {".ROBLOSECURITY": g}
c.cookies['.ROBLOSECURITY'] = g
csrftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details').headers['x-csrf-token']
values = requests.get(f"https://www.rolimons.com/itemapi/itemdetails").json()
#index 2 is rap, index 3 is value, index 4 is value (rap if not valued), index 7 is projected flag, 1 is projected, -1 is not
def testCookie():
    test = requests.get("https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=10",cookies=cookies)
    if test.status_code == 401:
        print("Invalid cookie, make sure to include warning")
        time.sleep(30)
        os._exit(0)
def getpages():
    headers = {'X-CSRF-TOKEN': csrftoken}
    count = 1
    try:
        nextpage = requests.get(f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100", cookies=cookies,headers=headers).json()['nextPageCursor']
        print("Got page 1")
    except KeyError:
        return
    if nextpage == "":
        return
    pages.append(nextpage)
    if nextpage != None:
        for i in pages:
            if i != None:
                count = count + 1
                response429 = True
                connectionError = False
                try:
                    nextpage = requests.get(
                        f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100&cursor={i}",
                        cookies=cookies, headers=headers)
                except:
                    print("Error")
                    connectionError = True
                time.sleep(60/speed)
                if connectionError or nextpage.status_code == 429:
                    print("Put on cooldown, retrying....")
                    while response429:
                        time.sleep(60 / speed)
                        try:
                            nextpage = requests.get(
                                f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100&cursor={i}",
                                cookies=cookies, headers=headers)
                        except:
                            print("Error")
                            continue
                        if nextpage.status_code == 200:
                            response429 = False
                            print("Out of cooldown, continuing...")
                pages.append(nextpage.json()['nextPageCursor'])
                print(f"Got page {str(count)}")
            else:
                del pages[-1]
def getTrades():
    headers = {'X-CSRF-TOKEN': csrftoken}
    try:
        nextData = getAPI(f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100",cookies,headers).json()['data']
    except KeyError:
        print("No trades!")
        return False
    tradesToDecline.append(nextData)
    if nextData != None:
        for i in pages:
            response429 = True
            connectionError = False
            try:
                nextData = requests.get(f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100&cursor={i}",cookies=cookies,headers=headers)
            except:
                print("Error")
                connectionError = True
            time.sleep(60/speed)
            if connectionError or nextData.status_code == 429:
                print("Put on cooldown, retrying...")
                while response429:
                    time.sleep(60 / speed)
                    try:
                        nextData = requests.get(
                            f"https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=100&cursor={i}",
                            cookies=cookies, headers=headers)
                    except:
                        print("Error")
                        continue
                    if nextData.status_code == 200:
                        response429 = False
                        print("Out of cooldown, continuing...")
            if nextData.status_code == 400:
                return True
            tradesToDecline.append(nextData.json()['data'])
        return True
def checkChanges(old,new):
    for item in itemChecked:
        if abs((old['items'][item][4]/new['items'][item][4])*100-100) >= change: return True
    return False
def cacheTrades():
    headers = {'X-CSRF-TOKEN': csrftoken}
    newcrsftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details')
    trade = 0
    for i in tradesToDecline:
        if i != None:
            for trades in i:
                trade = trade + 1
                if trade % 150 == 0:
                    try:
                        headers = makenewCSRF(newcrsftoken)
                    except:
                        print("Error")
                        continue
                if str(trades['id']) in tradesChecked: continue
                nextItems = getAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}", cookies, headers)
                tradesChecked[str(trades['id'])] = {"Sending": [nextItems.json()['offers'][0]['userAssets']], "Receiving": [nextItems.json()['offers'][1]['userAssets']], "Partner": nextItems.json()['offers'][1]['user']['id']}
                with open("tradesCached.json", "w") as write_file:
                    json.dump(tradesChecked, write_file)
    print(len(tradesChecked))


def makenewCSRF(newcsrftoken):
    response429CSRF = True
    time.sleep(60/speed)
    if newcsrftoken.status_code == 429:
        print("csrf rate limited")
        while response429CSRF:
            time.sleep(20)
            newcsrftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details')
            if newcsrftoken.status_code == 200:
                print("success csrf")
                response429CSRF = False
    headers = {'X-CSRF-TOKEN': newcsrftoken.headers['x-csrf-token']}
    print("got new csrf")
    return headers
def postAPI(url,security,headers):
    response429 = True
    connectionError = False
    try:
        postRequest = requests.post(url, cookies=security, headers=headers)
    except:
        print("Error")
        connectionError = True
    postRequest = requests.post(url, cookies=security,headers=headers)
    if connectionError or postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(20)
            try:
                postRequest = requests.post(url, cookies=security,
                                            headers=headers)
            except:
                print("Error")
                continue
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
def getAPI(url,security,headers):
    response429 = True
    connectionError = False
    getRequest = "e"
    try:
        getRequest = requests.get(url, cookies=security, proxies = proxies)
    except:
        print("Error")
        connectionError = True
    time.sleep(60/speed)
    if connectionError or getRequest.status_code == 429:
        print("Put on cooldown, retrying....")
        while response429:
            time.sleep(20)
            try:
                getRequest = requests.get(url, cookies=security, proxies = proxies)
            except requests.exceptions.RequestException as error:
                print("Error: ", error)
                continue
            if getRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
    return getRequest
def checkProj(items,header):
    print("Checking if projected...")
    for id in items:
        if id in cachedProjs: return True
        elif values["items"][id][3] != -1: continue
        price = getAPI(f"https://economy.roblox.com/v1/assets/{id}/resellers?cursor=&limit=10",cookies,header).json()
        if values["items"][id][2]/price['data'][0]['price'] >= ratio:
            return True
    return False

def checkTrades():
    for i in tradesToDecline:
        if i != None:
            for trades in i:
                tradeJson = tradesChecked[str(trades['id'])]
                sendingVal = 0
                receiveVal = 0
                sendingItems = []
                sendingValues = []
                sendingUAIDs = []
                receiveItems = []
                receiveValues = []
                receiveUAIDs = []
                for ind in tradeJson['Sending'][0]:
                    sendingVal = sendingVal + values['items'][str(ind["assetId"])][4]
                    sendingItems.append(ind["name"])
                    sendingValues.append(values['items'][str(ind["assetId"])][4])
                    sendingUAIDs.append(ind['id'])
                for ind in tradeJson['Receiving'][0]:
                    receiveVal = receiveVal + values['items'][str(ind["assetId"])][4]
                    receiveItems.append(ind["name"])
                    receiveValues.append(values['items'][str(ind["assetId"])][4])
                    receiveUAIDs.append(ind['id'])
                if receiveVal > sendingVal:
                    print(trades['id'])
                    if not checkInvs(tradeJson['Partner'], "", receiveUAIDs):
                        print("Trade not available, declined")
                        newcsrftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details')
                        headers = {'X-CSRF-TOKEN': newcsrftoken.headers['x-csrf-token']}
                        postAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}/decline", cookies, headers)
                        continue
                    if str(trades['id']) in winsSent: continue
                    print(webhook.send(f"--------------------------------- \n {str(trades['id'])}\n Win inbound! \n \n Sending: \n {str(sendingItems)} \n {str(sendingValues)} {sendingVal} \n \n Receiving: \n {str(receiveItems)} \n {str(receiveValues)} {receiveVal}"))
                    winsSent.append(str(trades['id']))
                    with open("winsSent.json", "w") as write_file:
                        json.dump({"IDs": winsSent}, write_file)
                    time.sleep(1)

def checkInvs(partner, page, items):
    itemsList = items
    if page == "":
        invInfo = getAPI(f"https://inventory.roblox.com/v1/users/{partner}/assets/collectibles?sortOrder=Asc&limit=100", cookies, "").json()
    else:
        invInfo = getAPI(f"https://inventory.roblox.com/v1/users/{partner}/assets/collectibles?sortOrder=Asc&limit=100&cursor={page}", cookies, "").json()
    try:
        testVar = invInfo["data"]
    except:
        print("user doesnt exist prob?")
        return False
    for i in invInfo['data']:
        if i["userAssetId"] in itemsList: del itemsList[itemsList.index(i["userAssetId"])]
    if invInfo['nextPageCursor'] != None and len(itemsList) > 0:
        return checkInvs(partner, invInfo['nextPageCursor'], itemsList)
        print("next page!!")
    elif len(itemsList) > 0:

        return False
    return True

while True:
    with open("tradesCached.json", "r") as read_file:
        tradesChecked = json.load(read_file)
    with open("winsSent.json", "r") as read_file:
        winsSent = json.load(read_file)['IDs']
    pages = []
    tradesToDecline = []
    values = requests.get(f"https://www.rolimons.com/itemapi/itemdetails").json()
    testCookie()
    print("Checking inbounds...")
    getpages()
    haveTrades = getTrades()
    oldValues = values
    newValues = requests.get(f"https://www.rolimons.com/itemapi/itemdetails").json()
    if haveTrades:
        cacheTrades()
        checkTrades()
    print("Finished checking, waiting " + str(cooldown) + " minutes!")
    time.sleep(cooldown*60)