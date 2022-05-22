import configparser
import json
import os
import time
from discord import WebhookAdapter, RequestsWebhookAdapter, Webhook
import numpy as np
import concurrent.futures
import threading
import requests
from bs4 import BeautifulSoup
class massSend():
    config = {}

    with open("config.json", "r") as file:
        config = json.load(file)

    sentUsers = []
    queue = []
    proxyList = config['proxyList']
    cookies = {".ROBLOSECURITY": config['auth']['cookie']}
    userID = config['auth']['userId']
    rotatingP = {"http": config['auth']['proxy'], "https": config['auth']['proxy']}
    webhookURL  = config['webhook']
    webhook = Webhook.from_url(webhookURL, adapter=RequestsWebhookAdapter())
    sending = config['trading']['sending']
    receive = config['trading']['receiveID']
    csrfTokensProxy = {}
    UAIDs = {}
    def sendTrade(self, headers, proxy):
        try:
            requested = requests.post("https://trades.roblox.com/v1/trades/send", json=self.queue[0], cookies=self.cookies, headers=headers, proxies = proxy)
        except requests.exceptions.RequestException as error:
            print(error)
            return
        except requests.exceptions.ConnectionError as error:
            print(error)
            return
        if requested.status_code != 429:
            if requested.status_code == 200:
                print(f"Sent to user {str(self.queue[0]['offers'][0]['userId'])} [{str(len(self.queue))} left in queue]")
            else:
                print(requested.json())
            del self.queue[0]
            time.sleep(7)
    def getOwner(self, id):
        result = []
        currentTime = time.time()
        tuff = self.getReq(f"https://www.rolimons.com/item/{id}").text
        soup = BeautifulSoup(tuff, "html.parser")
        scripts = soup.find_all("script")[21]
        data = str(scripts.string)
        index = data.find('{"num_bc_copies":')
        startInd = data.find("[", index)
        endingInd = data.find("]", startInd)
        onlineInd = data.find('"bc_last_online":')
        onlineStart = data.find("[", onlineInd)
        onlineTable = data[onlineStart + 1:data.find("]", onlineStart)].split(",")
        badTable = []
        strtable = data[startInd + 1:endingInd + 1]
        table = strtable.split(",")
        for i in range(len(table)):
            if currentTime - int(float(onlineTable[i])) > 14 * 60 * 60 * 24:
                badTable.append(table[i])
        finalArr = np.unique(table)
        for i in finalArr:
            result.append(i)
        return result

    def makenewCSRF(self, proxy):
        cookie = self.cookies
        response429 = True
        connectionError = False
        #try:
        postRequest = requests.post("https://catalog.roblox.com/v1/catalog/items/details", cookies=cookie, proxies=proxy)
        #except:
        #    print("Error")
        #    connectionError = True
        if connectionError or postRequest.status_code == 429:
            response429 = True
            while response429:
                time.sleep(20)
                try:
                    postRequest = requests.post("https://catalog.roblox.com/v1/catalog/items/details", cookies=cookie,
                                                proxies=proxy)
                except:
                    print("Error")
                    continue
                if postRequest.status_code == 200:
                    response429 = False
                    print("Out of cooldown, continuing...")
                print("Put on cooldown, retrying...")
        headers = {"X-CSRF-TOKEN": postRequest.headers["x-csrf-token"]}
        return headers

    def updateCSRF(self):
        while True:
            print("Updating CSRF of Proxies...")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.updateSing, self.proxyList)
            print("Done updating CSRFs")
            time.sleep(120)

    def updateSing(self, proxy):
        headers = self.makenewCSRF({"https": proxy, "http": proxy})
        self.csrfTokensProxy[proxy] = headers

    def getReq(self, url, cookieY=False):
        if cookieY: cookie = self.cookies
        else: cookie = {}
        response429 = True
        connectionError = False
        getRequest = "e"
        try:
            getRequest = requests.get(url, cookies=cookie, proxies=self.rotatingP)
        except:
            print("Error")
            connectionError = True
        time.sleep(.1)
        if connectionError or getRequest.status_code == 429:
            print("Put on cooldown, retrying....")
            print(url)
            while response429:
                time.sleep(20)
                try:
                    getRequest = requests.get(url, cookies=cookie, proxies=self.rotatingP)
                except requests.exceptions.RequestException as error:
                    print("Error: ", error)
                    continue
                if getRequest.status_code == 200:
                    response429 = False
                    print("Out of cooldown, continuing...")
        return getRequest
    def getIdFromInventory(self, userId):
        cursor = ""
        while cursor is not None:
            items = self.getReq(f"https://inventory.roblox.com/v1/users/{userId}/assets/collectibles?assetType=null&cursor={cursor}&limit=100",True).json()
            for item in items['data']:
                if self.receive == item['assetId']:
                    self.UAIDs[str(userId)] = item['userAssetId']
                    return
            cursor = items['nextPageCursor']
            time.sleep(1)

    def updateQueue(self):
        with open("queue.json", "w") as file:
            json.dump({"queue":self.queue}, file)

    def getQueue(self):
        with open("queue.json", "r") as file:
            self.queue = json.load(file)['queue']
    # Main


    def main(self):
        self.getQueue()
        counter = 0
        thread = threading.Thread(target=self.updateCSRF)
        thread.start()
        if not self.queue:
            users = self.getOwner(self.receive)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.getIdFromInventory, users)
            for i in users:
                if str(i) in self.UAIDs:
                    self.queue.append({"offers": [{"userId": int(i), "userAssetIds": [self.UAIDs[str(i)]], "robux": 0},
                                          {"userId": self.userID, "userAssetIds": self.sending,
                                           "robux": 0}]})
            print(f"Queued {len(self.queue)} trades")
        else:
            print(f"Existing queue of {len(self.queue)}")
        while len(self.queue) > 0:
            try:
                canTrade = self.getReq(f"https://trades.roblox.com/v1/users/{self.queue[0]['offers'][0]['userId']}/can-trade-with", True).json()
                if not canTrade['canTrade']:
                    del self.queue[0]
                    continue
            except:
                print(canTrade)
                continue
            if counter == 99:
                counter = 0
            proxyToUse = self.proxyList[counter]
            headers = self.csrfTokensProxy[proxyToUse]
            proxyToUse = {"http": proxyToUse, "https": proxyToUse}
            self.sendTrade(headers, proxyToUse)
            counter += 1
            self.updateQueue()
        self.webhook.send("Done massing")


myClass = massSend()
myClass.main()
