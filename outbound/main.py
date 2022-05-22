import configparser
import requests
import time
import os
pages = []
tradesToDecline = []
offers = []
c = requests.Session()
cachedProjs = []
cachedNotProj = []
tradesChecked = []
config = configparser.ConfigParser()
config.read('config.ini')
try:
    g = config['Authentication']['roblosecurityCookie']
    loss = int(config['Settings']['lossThreshold'])
    cooldown = int(config['Settings']['cooldownTime'])
    block = config['List']['itemsToAvoid'].split(",")
    ratio = float(config['Settings']['projectedVal'])
    keep = config['List']['itemsToKeep'].split(",")
    ignore = config['List']['itemsToIgnore'].split(",")
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

cookies = {".ROBLOSECURITY": g}
c.cookies['.ROBLOSECURITY'] = g
csrftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details').headers['x-csrf-token']
values = requests.get(f"https://www.rolimons.com/itemapi/itemdetails").json()
#index 2 is rap, index 3 is value, index 4 is value (rap if not valued), index 7 is projected flag, 1 is projected, -1 is not
def testCookie():
    test = requests.get("https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=10",cookies=cookies)
    if test.status_code == 401:
        print("Invalid cookie, make sure to include warning")
        time.sleep(30)
        os._exit(0)
def getpages():
    headers = {'X-CSRF-TOKEN': csrftoken}
    try:
        nextpage = requests.get(f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100", cookies=cookies,headers=headers).json()['nextPageCursor']
    except KeyError:
        return
    pages.append(nextpage)
    if nextpage != None:
        for i in pages:
            if i != None:
                response429 = True
                connectionError = False
                try:
                    nextpage = requests.get(f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100&cursor={i}", cookies=cookies)
                except requests.exceptions.RequestException as error:
                    print("Error: ", error)
                    connectionError = True
                time.sleep(.15)
                if connectionError or nextpage.status_code == 429:
                    print("Put on cooldown, retrying....")
                    while response429:
                        try:
                            nextpage = requests.get(
                                f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100&cursor={i}",
                                cookies=cookies)
                        except requests.exceptions.RequestException as error:
                            print("Error: ", error)
                            continue
                        if nextpage.status_code == 200:
                            response429 = False
                            print("Out of cooldown, continuing...")
                pages.append(nextpage.json()['nextPageCursor'])
            else:
                del pages[-1]
def getTrades():
    headers = {'X-CSRF-TOKEN': csrftoken}
    try:
        nextData = requests.get(f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100",cookies=cookies,headers=headers).json()['data']
    except KeyError:
        print("No trades!")
        return False
    tradesToDecline.append(nextData)
    if nextData != None:
        for i in pages:
            response429 = True
            connectionError = False
            try:
                nextData = requests.get(
                    f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100&cursor={i}", cookies=cookies,headers=headers)
            except requests.exceptions.RequestException as error:
                print("Error: ", error)
                connectionError = True
            time.sleep(.15)
            if connectionError or nextData.status_code == 429:
                print("Put on cooldown, retrying...")
                while response429:
                    try:
                        nextData = requests.get(
                            f"https://trades.roblox.com/v1/trades/Outbound?sortOrder=Asc&limit=100&cursor={i}",
                            cookies=cookies, headers=headers)
                    except requests.exceptions.RequestException as error:
                        print("Error: ", error)
                        continue
                    if nextData.status_code == 200:
                        response429 = False
                        print("Out of cooldown, continuing...")
            if nextData.status_code == 400:
                return True
            tradesToDecline.append(nextData.json()['data'])
        return True
def getItems():
    headers = {'X-CSRF-TOKEN': csrftoken}
    newcrsftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details')
    for i in tradesToDecline:
        headers = makenewCSRF(newcrsftoken)
        if i != None:
            for trades in i:
                nextItems = getAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}",cookies,headers)
                receiveValue = 0
                sendValue = 0
                receiveItems = []
                sendItems = []
                receiveIds = []
                sendIds = []
                receiveProj = False
                inBlockList = False
                inKeepList = False
                inIgnoreList = False
                for inbound in nextItems.json()['offers'][1]['userAssets']:
                    receiveItems.append(inbound['name'])
                    receiveIds.append(str(inbound['assetId']))
                    receiveValue = receiveValue + values["items"][f"{str(inbound['assetId'])}"][4]
                    if values["items"][str(inbound['assetId'])][7] == 1: receiveProj = True
                    for item in block:
                        if item == str(inbound['assetId']):
                            inBlockList = True
                            break

                for inbound in nextItems.json()['offers'][0]['userAssets']:
                    sendItems.append(inbound['name'])
                    sendIds.append(str(inbound['assetId']))
                    sendValue = sendValue + values["items"][f"{str(inbound['assetId'])}"][4]
                    if str(inbound['assetId']) in ignore:
                        inIgnoreList = True
                        break
                    for item in keep:
                        if item == str(inbound['assetId']):
                            inKeepList = True
                            break
                tradeOfferStr = f"Sending:{str(sendItems)} Value:{sendValue}, Recieving:{str(receiveItems)} Value:{receiveValue}"
                if inIgnoreList:
                    print(f"Ignored from list, {tradeOfferStr}")
                    continue
                if (receiveValue/sendValue)-1<=loss/100:
                    postAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}/decline",cookies,headers)
                    print(f"{str(receiveValue-sendValue)} Loss, {tradeOfferStr}")
                    continue
                if not receiveProj:
                    if not inBlockList and not inKeepList:
                        priceProj = checkProj(receiveIds, headers)
                        if not priceProj:
                            print(f"{str(receiveValue-sendValue)} Win, {tradeOfferStr}")
                        else:
                            print(f"Possibly a projected, {tradeOfferStr}")
                    else:
                        postAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}/decline", cookies, headers)
                        print(f"Declined from blocklist, {tradeOfferStr}")
                else:
                    postAPI(f"https://trades.roblox.com/v1/trades/{trades['id']}/decline", cookies, headers)
                    print(f"Projected, {tradeOfferStr}")
def makenewCSRF(newcsrftoken):
    response429CSRF = True
    time.sleep(.5)
    if newcsrftoken.status_code == 429:
        print("csrf rate limited")
        while response429CSRF:
            time.sleep(.5)
            newcsrftoken = c.post('https://catalog.roblox.com/v1/catalog/items/details')
            if newcsrftoken.status_code == 200:
                print("success csrf")
                response429CSRF = False
    headers = {'X-CSRF-TOKEN': newcsrftoken.headers['x-csrf-token']}
    print("got new csrf")
    return headers
def postAPI(url,security,headers):
    postRequest = requests.post(url, cookies=security,headers=headers)
    time.sleep(.3)
    if postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(.5)
            postRequest = requests.post(url, cookies=security,
                                        headers=headers)
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
def getAPI(url,security,headers):
    response429 = True
    connectionError = False
    getRequest = "e"
    try:
        getRequest = requests.get(url,cookies = security)
    except requests.exceptions.RequestException as error:
        print("Error: ", error)
        connectionError = True
    time.sleep(.3)
    if connectionError or getRequest.status_code == 429:
        print("Put on cooldown, retrying....")
        while response429:
            time.sleep(20)
            try:
                getRequest = requests.get(url,cookies = security)
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
        time.sleep(.1)
        if id in cachedProjs: return True
        elif values["items"][id][3] != -1: continue
        elif id in cachedNotProj: continue
        price = getAPI(f"https://economy.roblox.com/v1/assets/{id}/resellers?cursor=&limit=10",cookies,header).json()
        if values["items"][id][2]/price['data'][0]['price'] <= ratio:
            cachedNotProj.append(id)
            return False
        else:
            cachedProjs.append(id)
            return True
    return False
while True:
    pages = []
    tradesToDecline = []
    cachedNotProj = []
    cachedProjs = []
    testCookie()
    print("Checking outbounds...")
    getpages()
    haveTrades = getTrades()
    if haveTrades:
        getItems()
        cachedProjs = []
    time.sleep(cooldown*60)
    print(f"Checking done! Waiting {str(cooldown)} minutes...")
    values = requests.get(f"https://www.rolimons.com/itemapi/itemdetails").json()