import requests
import time
import os
import configparser
from discord import Webhook, RequestsWebhookAdapter

config = configparser.ConfigParser()
config.read('config.ini')

try:
    minPrice = int(config['Settings']['minPrice'])
    maxValue = int(config['Settings']['maxValue'])
    secondsVal = int(config['Settings']['sellUpdateInterval'])
    userID = str(int(config['Authentication']['robloxID']))
    g = config['Authentication']['roblosecurityCookie']
except:
    print("Does every value have the correct value?")
    time.sleep(30)
    os.exit(0)

cookies = {".ROBLOSECURITY": g}
discordId = config['Settings']['discordID']
webhookURL = config['Settings']['discordWebhook']
webhook = Webhook.from_url(webhookURL, adapter=RequestsWebhookAdapter())

def getAPI(url,cookie,cookieNeeded):
    response429 = True
    connectionError = False
    getRequest = "e"
    try:
        if cookieNeeded:
                getRequest = requests.get(url, cookies=cookie)
        else:
            getRequest = requests.get(url)
    except:
        print("Error")
        connectionError = True
    if connectionError or getRequest.status_code == 429:
        print("Put on cooldown, retrying....")
        if not connectionError: print(getRequest.text)
        else: print("Error with connection")
        while response429:
            time.sleep(20)
            try:
                if cookieNeeded:
                    getRequest = requests.get(url, cookies=cookie)
                else:
                    getRequest = requests.get(url)
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
        postRequest = requests.post(url, cookies=cookie, headers=headers,json=payload)
    except:
        print("Error")
        connectionError = True
    if connectionError or postRequest.status_code == 429:
        response429 = True
        while response429:
            time.sleep(20)
            try:
                postRequest = requests.post(url, cookies=cookie,
                                            headers=headers,json=payload)
            except:
                print("Error")
                continue
            if postRequest.status_code == 200:
                response429 = False
                print("Out of cooldown, continuing...")
            print("Put on cooldown, retrying...")
    return postRequest

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

while True:
    inventory = getAPI(f"https://inventory.roblox.com/v1/users/244813380/assets/collectibles?assetType=null&cursor=&limit=50&sortOrder=Desc","",False).json()
    print(inventory)
    headers = makenewCSRF(cookies)
    for i in inventory['data']:
        nextSellerLoc = 0
        if i['assetId'] == 532254782: continue
        if i['recentAveragePrice'] > maxValue: continue
        salesdata = getAPI(f'https://economy.roblox.com/v1/assets/{i["assetId"]}/resellers?cursor=&limit=10', cookies, True).json()
        try:
            test = salesdata['data']
        except:
            print(salesdata)
        if salesdata['data'][0]['seller']['id'] == int(userID):
            if salesdata['data'][1]['price'] != salesdata['data'][0]['price'] + 1:
                postAPI("https://www.roblox.com/asset/toggle-sale", headers, cookies,
                        {'assetId': i['assetId'], 'userAssetId': i['userAssetId'], 'price': 0, 'sell': False})
                postAPI("https://www.roblox.com/asset/toggle-sale", headers, cookies,
                        {'assetId': i['assetId'], 'userAssetId': i['userAssetId'],
                         'price': salesdata['data'][1]['price'] - 1, 'sell': True})
            continue
        if salesdata['data'][0]['price'] <= minPrice:
            print(f"The lowest reseller is below {str(minPrice)}")
            continue
        for offer in range(len(salesdata['data'])):
            try:
                if salesdata['data'][offer]['seller']['id'] != salesdata['data'][offer+1]['seller']['id']:
                    nextSellerLoc = offer+1
                    break
            except:
                print("Next seller was not found")
                print(i["name"])
        if nextSellerLoc == 0: continue
        if salesdata['data'][0]['price'] < i['recentAveragePrice'] and (salesdata['data'][0]['price'] * 1.05 < salesdata['data'][nextSellerLoc]['price'] or salesdata['data'][0]['price'] < i['recentAveragePrice']):
            print("Low price detected, continuing...")
            print(i['name'])
            continue
        webhook.send(f"You should sell {i['name']} at {salesdata['data'][0]['price']-1}\nLink: https://www.roblox.com/catalog/{str(i['assetId'])}")
        postAPI("https://www.roblox.com/asset/toggle-sale",headers,cookies,{'assetId':i['assetId'],'userAssetId':i['userAssetId'],'price':0,'sell':False})
        postAPI("https://www.roblox.com/asset/toggle-sale", headers, cookies,{'assetId': i['assetId'], 'userAssetId': i['userAssetId'], 'price': salesdata['data'][0]['price']-1, 'sell': True})
        time.sleep(1)

    print("Scan done")
    time.sleep(secondsVal)