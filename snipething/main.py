import requests
import time
import os
import configparser
from discord import Webhook, RequestsWebhookAdapter
import timeit
c = requests.Session()
roli = requests.Session()

config = configparser.ConfigParser()
config.read('config.ini')

try:
    minPercentVal = int(config['Settings']['minPercent'])
    countVal = int(config['Settings']['valueUpdateInterval'])
    g = config['Authentication']['roblosecurityCookie']
except:
    print("Does every value have the correct value?")
    time.sleep(30)
    os.exit(0)

unbannedTime = [2,9,27]

#with open('counter.txt','r+') as file:
#    letter = file.read()
#    print(letter)
#    print("read", type(file.read()))
#    try:
#        if int(letter) != 0: file.write("0")
#    except:
#        print("error")
#        file.write("0")
#    file.write(str(int(letter) + 1))


cookies = {".ROBLOSECURITY": g}
discordId = config['Settings']['discordID']
webhookURL = config['Settings']['discordWebhook']
webhook = Webhook.from_url(webhookURL, adapter=RequestsWebhookAdapter())
webhook2 = Webhook.from_url("https://discord.com/api/webhooks/954899574902902865/ESoEOosAYj89-MeGTNQL__1rR1rWu3KM57Pk_EDEs5vCYEUJ5Rmw39h9BYUKmiT3HJNs   ", adapter = RequestsWebhookAdapter())
RAP_THRESHOLD = {5000:4000,6000:4700,7000:5400,8000:6200,9000:7000,10000:7800,11000:8600,12000:9400,13000:10000,14000:10800,15000:11600,16000:12400,18000:14000,20000:15500,22000:17000,24000:18500,26000:20000,28000:21500,30000:23000,32000:25000,35000:27000,38000:29000,40000:31000,42000:33000,45000:35000,48000:37000,50000:40000,55000:43000}
if requests.get("https://trades.roblox.com/v1/trades/Inbound?sortOrder=Asc&limit=10",cookies = cookies).status_code == 401:
    print("Check your cookie")
    time.sleep(30)
    os.exit(0)

webhook.send("Starting...")

print(f"config: updating value every {str(countVal)} times and sniping for deals over {minPercentVal}%")

time.sleep(2)

projlist = {}

c.cookies['.ROBLOSECURITY'] = g
proxies={
        "http": "http://epkdhlyr-rotate:8vjn240pwn2j@p.webshare.io:80/",
        "https": "http://epkdhlyr-rotate:8vjn240pwn2j@p.webshare.io:80/"
}

def getAPI(url,cookie,cookieNeeded):
    response429 = True
    connectionError = False
    getRequest = "e"
    try:
        if cookieNeeded:
                getRequest = c.get(url)
        else:
            getRequest = roli.get(url)
    except:
        print("Error")
        connectionError = True
    if connectionError or getRequest.status_code == 429:
        #with open('counter.txt', 'r') as read_file:
        #    with open('counter.txt', "w") as write_file:
        ##        try:
        ##            if int(read_file.read()) > 10:
        ##                for i in range(3): webhook.send("Program down! Restart now!")
        ##            write_file.write(str(int(read_file.read()) + 1))
         #       except:
         #           print("Error with file")
        print("Put on cooldown, retrying....")
        print(url)
        if not connectionError:
            print(getRequest.text)
        else:
            print("Error with connection")
        while response429:
            time.sleep(20)
            try:
                if cookieNeeded:
                    getRequest = c.get(url)
                else:
                    getRequest = roli.get(url)
            except requests.exceptions.RequestException as error:
                print("Error: ", error)
                continue
            if getRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
    return getRequest

def postAPI(url,headers,cookie,payload):
    response429 = True
    connectionError = False
    postRequest = ""
    try:
        postRequest = c.post(url, headers=headers,json=payload)
    except:
        print("Error")
        connectionError = True
    if connectionError or postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(20)
            try:
                postRequest = c.post(url,
                                            headers=headers,json=payload)
            except:
                print("Error")
                continue
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
            print(url)
    webhook.send(postRequest.json())
    webhook.send(postRequest.status_code)
def makenewCSRF(cookie):
    response429 = True
    connectionError = False
    try:
        postRequest = requests.post('https://catalog.roblox.com/v1/catalog/items/details',cookies = cookie)
    except:
        print("Error")
        connectionError = True
    postRequest = requests.post('https://catalog.roblox.com/v1/catalog/items/details',cookies = cookie)
    if connectionError or postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(20)
            try:
                postRequest = requests.post('https://catalog.roblox.com/v1/catalog/items/details', cookies=cookie)
            except:
                print("Error")
                continue
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
    headers = {'X-CSRF-TOKEN': postRequest.headers['x-csrf-token']}
    print("got new csrf")
    return headers
def updatePresence(url, headers, payload):
    response429 = True
    connectionError = False
    postRequest = ""
    try:
        postRequest = c.post(url, headers=headers, json=payload)
    except:
        print("Error")
        connectionError = True
    if connectionError or postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(20)
            try:
                postRequest = c.post(url,
                                     headers=headers, json=payload)
            except:
                print("Error")
                continue
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
            print(url)


while True:
    value = getAPI("https://www.rolimons.com/itemapi/itemdetails","",False).json()
    headers = makenewCSRF(cookies)
    updatePresence("https://presence.roblox.com/v1/presence/register-app-presence", headers, {"location": "CatalogItem"})
    for i in range(30):
        time.sleep(3)
        prices = getAPI('https://www.rolimons.com/api/activity2','',False).json()
        for item in prices['activities']:
            try:
                testVariable = item[4]
            except:
                print(item)
                continue
            id = item[2]
            name = value['items'][id][0]
            isValued = value['items'][id][3] != -1
            if value['items'][id][4] == 0: continue
            if 1 - item[4]/value['items'][id][4] >= minPercentVal/100:
                if item[4] == 0: continue
                if value['items'][id][4] <= 1000:
                    if not item[4] <= 300: continue
                if id in projlist:
                    if 1 - value['items'][id][4] / projlist[id] >= 0.1:
                        print(f"Deleted {name} from proj list")
                        del projlist[id]
                    else:
                        continue
                start = time.time()
                salesdata = getAPI(f'https://economy.roblox.com/v1/assets/{id}/resellers?cursor=&limit=10',cookies,True).json()
                end = time.time()
                try:
                    testVariable = salesdata['data'][0]['price']
                except:
                    print(salesdata)
                    continue
                if value["items"][id][7] == 1 and not isValued:
                    print(f"{name} is marked")
                    print(str(end-start))
                    projlist[id] = value['items'][id][4]
                    continue
                if salesdata['data'][1]['price'] * 1.1 <= value['items'][id][4] and not isValued:
                    print(f"{name} is proj")
                    print(str(end - start))
                    projlist[id] = value['items'][id][4]
                    continue
                if 1 - item[4]/value['items'][id][4] <= 0.35 and isValued and not value['items'][id][2]/RAP_THRESHOLD[value['items'][id][3]] >= 0.95:
                    print(f"{name} is underrap")
                    continue
                if salesdata['data'][0]['price'] != item[4]:
                    print(salesdata['data'][0]['price'],item[4],id)
                    print("Missed deal :(")
                    webhook2.send(f"Link: https://www.roblox.com/catalog/{str(id)}\nItem: {name}\nPrice: {str(item[4])}\nCurrrent Value: {str(value['items'][id][4])}")
                    webhook2.send(f"{salesdata['data'][0]['seller']['id']} sold the missed deal")
                    webhook2.send(str(end-start))
                    print(prices["activities"])
                    continue
                print(f"Found deal for {str(100*(1 - item[4]/value['items'][id][4]))}%, item is {name}")
                productID = getAPI(f"https://api.roblox.com/Marketplace/ProductInfo?assetId={str(id)}",cookies,True).json()['ProductId']
                postAPI(f"https://economy.roblox.com/v1/purchases/products/{str(productID)}",headers,cookies,{"expectedCurrency": 1,"expectedPrice": item[4],"expectedSellerId": salesdata['data'][0]['seller']['id'],"userAssetId":salesdata['data'][0]['userAssetId']})
                webhook.send(str({"expectedCurrency": 1,"expectedPrice": item[4],"expectedSellerId": salesdata['data'][0]['seller']['id'],"userAssetId":salesdata['data'][0]['userAssetId']}))
                webhook.send(f"Link: https://www.roblox.com/catalog/{str(id)}\nItem: {name}\nPrice: {str(item[4])}\nCurrrent Value: {str(value['items'][id][4])}")
