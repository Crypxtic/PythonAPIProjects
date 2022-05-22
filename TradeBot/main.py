
import requests
import time
import json
from bs4 import BeautifulSoup
import numpy as np
import os
import random
import threading
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import concurrent.futures
from itertools import combinations


class tradeBot():
    ownItems = []
    itemList = []
    config = {}
    usersToSend = {}
    sentUsers = []
    itemsToScan = []
    itemsAlreadyScanned = []
    valuesJSON = {}
    selfTrades = []
    nextOverrideTime = 0
    values = {}
    mainQueue = []
    indvProxies = []
    updatingVals = False
    queueVals = {}
    sentTrades = []
    inventories = {}
    csrfTokensProxy = {}
    threadUsers = {}
    nextQueueExpire = 0
    retries = 0
    lastOutboundUpdate = 0
    outbound = {}
    getRidOfFast = 0
    isMassSend = False
    massReceive = 0
    massSend = []

    with open("config.json", "r") as read_file:
        config = json.load(read_file)
    proxies = {"https": config["authentication"]["proxy"], "http": config["authentication"]["proxy"]}
    cookies = {".ROBLOSECURITY": config["authentication"]["robloxSecurityCookie"]}

    def updateRolis(self):
        try:
            self.values = self.getReq("https://www.rolimons.com/itemapi/itemdetails").json()["items"]
        except:
            print("Problem with getting values")
            self.updateRolis()

    def getTradeAds(self):
        users = {}
        try:
            tradeAdsPage = self.getReq("https://www.rolimons.com/trades")
            soup = BeautifulSoup(tradeAdsPage.text, "html.parser")
            script = str(soup.find_all("script")[-2])
            start = script.find("trade_ads        =")
            tradeAds = script[start:script.find(";", start)]
            trades = json.loads(tradeAds[tradeAds.find("["):])
        except:
            return self.getTradeAds()
        for i in trades:
            # DG is 6
            # Upg is 5
            upgrade = False
            downgrade = False
            if "tags" in i[5]:
                for ind in i[5]["tags"]:
                    if ind == 5:
                        upgrade = True
                    elif ind == 6:
                        downgrade = True
                if upgrade and downgrade:
                    upgrade = False
                    downgrade = False
                userJSON = {"upgrade": upgrade, "downgrade": downgrade, "priority": upgrade or downgrade}
                if str(i[2]) in users:
                    if upgrade or downgrade:
                        if not users[str(i[2])]["priority"]:
                            users[str(i[2])] = userJSON
                else:
                    users[str(i[2])] = userJSON
        return users

    def getOwner(self, id):
        result = {}
        currentTime = time.time()
        try:
            tuff = self.getReq(f"https://www.rolimons.com/item/{id}").text
            soup = BeautifulSoup(tuff, "html.parser")
            scripts = soup.find_all("script")[21]
            data = str(scripts.string)
            index = data.find('{"num_bc_copies":')
            startInd = data.find("[", index)
            endingInd = data.find("]", startInd)
            onlineInd = data.find('"bc_last_online":')
            onlineStart = data.find("[", onlineInd)
            salesStart = data.find("avg_daily_sales_volume_30_days = ")
            salesStart = data.find("=", salesStart)
            onlineTable = data[onlineStart + 1:data.find("]", onlineStart)].split(",")
            salesNum = float(data[salesStart+1:data.find(";", salesStart)])
            if salesNum < 1.5: return {}
            badTable = []
            strtable = data[startInd + 1:endingInd + 1]
            table = strtable.split(",")
            for i in range(len(table)):
                if currentTime - int(float(onlineTable[i])) > 14 * 60 * 60 * 24:
                    badTable.append(table[i])
            finalArr = np.unique([x for x in table if x not in badTable])
            for i in finalArr:
                result[i] = {"upgrade": False, "downgrade": False, "priority": False}
            return result
        except:
            return {}

    def getItems(self, userID, items=[], cursor=""):
        if cursor == "" or userID == self.config['authentication']['userId']:
            items = []
            self.updateRolis()
        values = self.values
        inventoryCall = self.getReq(
            f"https://inventory.roblox.com/v1/users/{userID}/assets/collectibles?assetType=null&cursor={cursor}&limit=100").json()
        if "errors" in inventoryCall:
            print("Error with inventory!")
            if inventoryCall["errors"][0]["code"] == 11: print("Private Inventory!!")
            return []
        for i in inventoryCall["data"]:
            if str(i["assetId"]) not in self.valuesJSON or self.valuesJSON[str(i["assetId"])]["correctedVal"] == 0:
                if str(i["assetId"]) not in self.valuesJSON:
                    self.valuesJSON[str(i["assetId"])] = {"actualVal": values[str(i["assetId"])][4],
                                                              "correctedVal": 0, "projected": False,
                                                              "nextCheck": time.time() + 50}
                items.append({"assetId": i["assetId"], "userAssetId": i["userAssetId"], "name": i["name"],
                              "RAP": values[str(i["assetId"])][4]})
            else:

                items.append({"assetId": i["assetId"], "userAssetId": i["userAssetId"], "name": i["name"],
                              "RAP": self.valuesJSON[str(i["assetId"])]["correctedVal"]})
        if inventoryCall["nextPageCursor"] != None:
            return self.getItems(userID, items, inventoryCall["nextPageCursor"])
        else:
            return items

    def getRAP(self, item):
        return item.get("RAP")

    def getReq(self, url, cookie={}):
        proxy = self.proxies
        response429 = True
        connectionError = False
        getRequest = "e"
        try:
            getRequest = requests.get(url, cookies=cookie, proxies=proxy)
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
                    getRequest = requests.get(url, cookies=cookie, proxies=proxy)
                except requests.exceptions.RequestException as error:
                    print("Error: ", error)
                    continue
                if getRequest.status_code == 200:
                    response429 = False
                    print("Out of cooldown, continuing...")
        return getRequest

    def postReq(self, url, payload, headers, cookie, proxy, ignore429 = False):
        response429 = True
        connectionError = False
        postRequest = ""
        try:
            postRequest = requests.post(url, headers=headers, json=payload, cookies=cookie, proxies=proxy)
        except:
            print("Error")
            connectionError = True
        if connectionError or postRequest.status_code == 429:
            if ignore429: return postRequest
            response429 = True
            while response429:
                time.sleep(20)
                try:
                    postRequest = requests.post(url, headers=headers, json=(payload), cookies=cookie, proxies=proxy)
                except:
                    print("Error")
                    continue
                if postRequest.status_code == 200:
                    response429 = False
                    print("Out of cooldown, continuing...")
                print("Put on cooldown, retrying...")
                print(url)
        return postRequest

    def makenewCSRF(self, cookie, proxy):
        response429 = True
        connectionError = False
        try:
            postRequest = requests.post("https://catalog.roblox.com/v1/catalog/items/details", cookies=cookie, proxies=proxy)
        except:
            print("Error")
            connectionError = True
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

    def checkDupes(self, existing, new):
        return np.unique(existing.extend(new))

    def updateJSON(self):
        with open("users.json", "w") as write_file:
            usersJson = {"users": self.usersToSend, "sent": self.sentUsers, "overrideTime": self.nextOverrideTime}
            json.dump(usersJson, write_file)
        with open("itemsScan.json", "w") as write_file:
            itemsJson = {"toScan": self.itemsToScan, "scanned": self.itemsAlreadyScanned}
            json.dump(itemsJson, write_file)

    def getOutbound(self):
        with open("outbound.json", "r") as file:
            jsonThing = json.load(file)
            self.outbound = jsonThing["outbound"]
            self.lastOutboundUpdate = jsonThing["nextUpdate"]

    def updateOutbound(self):
        with open("outbound.json", "w") as file:
            fileJSON = {"outbound": self.outbound, "nextUpdate": self.lastOutboundUpdate}
            json.dump(fileJSON, file)

    def getUsersJ(self):
        with open("users.json", "r") as read_file:
            file = json.load(read_file)
            if file['overrideTime'] > time.time():
                self.usersToSend = file["users"]
                self.sentUsers = file["sent"]
                self.nextOverrideTime = file['overrideTime']

    def getItemsJ(self):
        with open("itemsScan.json", "r") as read_file:
            self.itemsToScan = json.load(read_file)["toScan"]
            self.itemsAlreadyScanned = json.load(read_file)["scanned"]

    def postValues(self):
        with open("value.json", "w") as write_file:
            json.dump({"items": self.valuesJSON}, write_file)

    def getValues(self):
        with open("value.json", "r") as read_file:
            self.valuesJSON = json.load(read_file)["items"]

    def scrapeFlip(self):
        result = {}
        flipJ = {}
        try:
            flipJ = self.getReq("https://legacy.rbxflip-apis.com/users/versus-history").json()
        except:
            print("Error with flip scrape")
            return {}
        if flipJ["ok"]:
            for i in flipJ["data"]["coinflips"]:
                if i["status"] == "Completed":
                    if not str(i["winner"]["id"]) in result: result[str(i["winner"]["id"])] = {"upgrade": False,
                                                                                               "downgrade": False,
                                                                                               "priority": False}
            return result
        else:
            print("something wrong happened! trying again")
            return self.scrapeFlip()

    def scrapePot(self):
        result = {}
        potJ = {}
        try:
            potJ = self.getReq("https://legacy.rbxflip-apis.com/users/jackpot-history").json()
        except:
            print("Error with pot scrape")
            return {}
        if potJ["ok"]:
            for i in potJ["data"]["jackpots"]:
                if i["status"] == "Completed":
                    if not str(i["winner"]["id"]) in result: result[str(i["winner"]["id"])] = {"upgrade": False,
                                                                                               "downgrade": False,
                                                                                               "priority": False}
            return result
        else:
            print("something wrong happened! trying again")
            return self.scrapePot()

    def scrapeRoPro(self, page=0):
        try:
            tradesJSON = self.getReq(f"https://api.ropro.io/getWishlistAll.php?page={page}").json()["wishes"]
        except:
            return
        for i in tradesJSON:
            upgrade = False
            downgrade = False
            user = i["user"]
            # Upgrade Check
            if i["item"]["id"] == "-4" or i["item2"]["id"] == "-4" or i["item3"]["id"] == "-4" or i["item4"][
                "id"] == "-4": upgrade = True
            # Dg Check
            if i["item"]["id"] == "-5" or i["item2"]["id"] == "-5" or i["item3"]["id"] == "-5" or i["item4"][
                "id"] == "-5": downgrade = True
            if upgrade and downgrade:
                upgrade = False
                downgrade = False
            userJSON = {"upgrade": upgrade, "downgrade": downgrade, "priority": upgrade or downgrade}
            if user in self.usersToSend:
                if upgrade or downgrade:
                    if not self.usersToSend[user]["priority"]:
                        self.usersToSend[user] = userJSON
            else:
                self.usersToSend[user] = userJSON
        if page <= 100: self.scrapeRoPro(page + 1)

    def singOwners(self, itemsArr):
        while len(self.usersToSend) < 3000:
            randomInd = random.randint(0, len(itemsArr))
            ownersJson = self.getOwner(itemsArr[randomInd])
            for i in ownersJson:
                if not i in self.usersToSend:
                    self.usersToSend[str(i)] = {"upgrade": False, "downgrade": False, "priority": False}

    def generateUsers(self):
        counter = 0
        inventory = self.getItems(self.config["authentication"]["userId"])
        inventory.sort(key=self.getRAP, reverse=True)
        itemsArr = []
        self.updateRolis()
        items = self.values
        totalTop4 = 0
        minValue = 0
        minPerc = self.config["trading"]["percentages"]["minValueGain"]
        maxPerc = self.config["trading"]["percentages"]["maxValueGain"]
        for i in range(4):
            totalTop4 += items[str(inventory[i]["assetId"])][4]
        for i in inventory:
            if items[str(i["assetId"])][4] > self.config["trading"]["minTradeValue"]:
                minValue = items[str(i["assetId"])][4]
        for i in items:
            if items[i][4] < maxPerc * totalTop4 and items[i][4] > minPerc * minValue:
                itemsArr.append(i)
        threads = []
        for i in range(25):
            time.sleep(.1)
            thread = threading.Thread(target=self.singOwners, args=(itemsArr,))
            thread.daemon = True
            threads.append(thread)
        for i in range(25):
            threads[i].start()
        for i in range(25):
            threads[i].join()

    def generateSelfTrade(self, userId):
        inventoryJSON = self.getItems(userId)
        getRidOfFast = self.getRidOfFast
        self.updateValues()
        customValues = self.config['trading']['customValues']
        result = []
        inventoryArr = []
        currentTime = time.time()
        time.sleep(5)
        for i in inventoryJSON:
            if self.valuesJSON[str(i["assetId"])]["correctedVal"] == 0:
                while self.valuesJSON[str(i["assetId"])]["correctedVal"] == 0:
                    print("Waiting for value update.....")
                    self.updateValues()
                    time.sleep(50)
            self.ownItems.append({"assetId": i["assetId"], "UAID": i["userAssetId"]})
            if str(i['assetId']) in customValues:
                inventoryArr.append(
                    {"UAID": i["userAssetId"], "RAP": customValues[str(i["assetId"])],
                     "assetId": i["assetId"]})
                continue
            if self.valuesJSON[str(i["assetId"])]["projected"] or self.values[str(i["assetId"])][3] != -1:
                inventoryArr.append({"UAID": i["userAssetId"], "RAP": self.valuesJSON[str(i["assetId"])]["correctedVal"],
                                 "assetId": i["assetId"]})
                continue
            inventoryArr.append({"UAID": i["userAssetId"], "RAP": self.values[str(i["assetId"])][4],
                                 "assetId": i["assetId"]})
        for i in inventoryArr:
            for i2 in inventoryArr:
                for i3 in inventoryArr:
                    for i4 in inventoryArr:
                        resultTHING = {}
                        mylist = list(np.sort(np.unique([i["UAID"], i2["UAID"], i3["UAID"], i4["UAID"]])))
                        if getRidOfFast != 0:
                            if getRidOfFast not in mylist: continue
                        listExists = False
                        for index in result:
                            if index["UAIDS"] == mylist:
                                listExists = True
                                break
                        if listExists: continue
                        myAssetList = list(
                            np.sort(np.unique([i["assetId"], i2["assetId"], i3["assetId"], i4["assetId"]])))
                        resultTHING = {"UAIDS": [int(x) for x in mylist], "assetId": [int(x) for x in myAssetList]}
                        rap = 0
                        if i["UAID"] in mylist:
                            mylist.remove(i["UAID"])
                            rap += i["RAP"]
                        if i2["UAID"] in mylist:
                            mylist.remove(i2["UAID"])
                            rap += i2["RAP"]
                        if i3["UAID"] in mylist:
                            mylist.remove(i3["UAID"])
                            rap += i3["RAP"]
                        if i4["UAID"] in mylist:
                            mylist.remove(i4["UAID"])
                            rap += i4["RAP"]
                        resultTHING["RAP"] = rap
                        result.append(resultTHING)
        result.sort(key=self.getRAP)
        return result

    def generateInv(self):
        self.updateRolis()
        self.inventories = {}
        usersKey = list(self.usersToSend.keys())
        random.shuffle(usersKey)
        maxL = 70
        if len(usersKey) < 70: maxL = len(usersKey)
        print(f"Getting inventories of {maxL} users")
        users = usersKey[0:maxL]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.singleInv, users)
        time.sleep(5)
        self.updateValues()

    def singleInv(self, user):
        self.inventories[str(user)] = self.getItems(user)

    def singleVal(self, i):
        roliVal = self.values
        currentTime = time.time()
        time.sleep(random.randint(1,2))
        if self.valuesJSON[i]["projected"]:
            if self.valuesJSON[i]['correctedVal'] >= 2500:
                resellers = self.getReq(f"https://economy.roblox.com/v1/assets/{i}/resellers?cursor=&limit=100").json()
                if resellers['data'][0]['price'] > self.valuesJSON[i]['actualVal']: self.valuesJSON[i][
                    "projected"] = False
        if self.valuesJSON[i]["nextCheck"] <= currentTime:
            itemInfo = roliVal[i]
            if itemInfo[3] != -1:
                if itemInfo[6] == 0 or itemInfo[6] == 1:
                    finalVal = itemInfo[4]
                    if finalVal <= 18000:
                        finalVal -= 1000
                    elif finalVal <= 42000:
                        finalVal -= 2000
                    elif finalVal <= 85000:
                        finalVal -= 5000
                    elif finalVal <= 250000:
                        finalVal -= 10000
                    else:
                        finalVal = finalVal * 0.93
                    self.valuesJSON[i]["correctedVal"] = finalVal
                elif itemInfo[6] == 3:
                    self.valuesJSON[i]["correctedVal"] = itemInfo[4] * 1.1
            elif self.valuesJSON[i]["projected"] or roliVal[i][7] == 1:
                if self.valuesJSON[i]['correctedVal'] >= 2500:
                    resellers = self.getReq(f"https://economy.roblox.com/v1/assets/{i}/resellers?cursor=&limit=100").json()
                    if resellers['data'][0]['price'] > self.valuesJSON[i]['actualVal']: self.valuesJSON[i]["projected"] = False
                pricePoints = []
                salesData = self.getReq(f"https://economy.roblox.com/v1/assets/{i}/resale-data").json()
                for index in salesData["priceDataPoints"]:
                    pricePoints.append(index["value"])
                average = (np.percentile(pricePoints, 25) + np.percentile(pricePoints, 50) + np.percentile(
                    pricePoints, 75)) / 3
                self.valuesJSON[i]["correctedVal"] = int(average)
                self.valuesJSON[i]["projected"] = True
            else:
                salesData = self.getReq(f"https://economy.roblox.com/v1/assets/{i}/resale-data").json()
                pricePoints = []
                for index in salesData["priceDataPoints"]:
                    if "2022" in index["date"]:
                        pricePoints.append(index["value"])
                if pricePoints == []:
                    for index in salesData["priceDataPoints"]:
                        pricePoints.append(index["value"])
                average = (np.percentile(pricePoints, 25) + np.percentile(pricePoints, 50) + np.percentile(
                    pricePoints, 75)) / 3
                if average * 1.25 < salesData["recentAveragePrice"]:
                    if self.valuesJSON[i]['correctedVal'] >= 2500:
                        resellers = self.getReq(
                            f"https://economy.roblox.com/v1/assets/{i}/resellers?cursor=&limit=100").json()
                        if resellers['data'][0]['price'] > self.valuesJSON[i]['actualVal']: self.valuesJSON[i][
                            "projected"] = False
                        else: self.valuesJSON[i]["projected"] = True
                else:
                    self.valuesJSON[i]["projected"] = False
                self.valuesJSON[i]["correctedVal"] = average
                time.sleep(.1)
            self.valuesJSON[i]["actualVal"] = itemInfo[4]
            self.valuesJSON[i]["nextCheck"] = currentTime + random.randint(1000, 7200)
    def updateValues(self):
        print("Getting Values!")
        self.queueVals = self.valuesJSON.copy()
        self.updatingVals = True
        self.updateRolis()
        thing = {}
        currentTime = time.time()
        counter = 0
        for i in self.valuesJSON:
            if self.valuesJSON[i]["nextCheck"] <= currentTime:
                thing[i] = self.valuesJSON[i]
                counter += 1
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.singleVal, thing)
        self.postValues()
        self.updatingVals = False
        print(f"Checked {counter} items!")
        for i in self.queueVals:
            if i not in self.valuesJSON: self.valuesJSON[i] = self.queueVals[i]

    def scrapeMain(self):
        self.getUsersJ()
        print("Starting scrape....")
        jackpot = self.scrapePot()
        coinflip = self.scrapeFlip()
        tradeAds = self.getTradeAds()
        t1 = threading.Thread(target=self.generateUsers)
        t2 = threading.Thread(target=self.scrapeRoPro)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        print("Scrape done")
        for i in tradeAds:
            if not i in self.usersToSend:
                self.usersToSend[i] = tradeAds[i]
            else:
                if not self.usersToSend[i]["priority"]: self.usersToSend[i] = tradeAds[i]
        for i in jackpot:
            if not i in self.usersToSend: self.usersToSend[i] = jackpot[i]
        for i in coinflip:
            if not i in self.usersToSend: self.usersToSend[i] = coinflip[i]
        print(len(self.usersToSend))
        self.nextOverrideTime = time.time() + 1800
        self.updateJSON()
        while True:
            if time.time() > self.nextOverrideTime or len(self.sentUsers) == len(self.usersToSend): self.scrapeMain()
            time.sleep(30)

    def generateQueue(self):
        focusOnFlipping = self.config["trading"]["focusOnProjectedFlipping"]
        minGain = self.config["trading"]["percentages"]["minValueGain"]
        maxGain = self.config["trading"]["percentages"]["maxValueGain"]
        myValues = self.valuesJSON
        myTrades = self.selfTrades
        maxTop4 = 0
        self.getQueue()
        if self.nextQueueExpire == 0: self.nextQueueExpire = time.time() + 1800
        if focusOnFlipping:
            while True:
                for i in self.ownItems:
                    if self.valuesJSON[str(i["assetId"])]["projected"] and self.valuesJSON[str(i["assetId"])]["actualVal"] > 3000:
                        self.getRidOfFast = i['UAID']
                        break
                if self.getRidOfFast == 0:
                    self.isMassSend = True
                    self.updateRolis()
                    for i in self.values:


        for i in range(len(myTrades)):
            if i == 3: break
            maxTop4 += myTrades[-1 * i - 1]["RAP"]
        time.sleep(10)
        counter = 0
        while True:
            self.generateInv()
            for i in self.inventories:
                time.sleep(6)
                if counter == 10:
                    counter = 0
                    self.updateQueue()
                counter += 1
                inventoryArr = []
                skipped = []
                users = self.usersToSend
                while True:
                    if users: break
                    time.sleep(5)
                if i in self.sentUsers: continue
                items = self.inventories[i]
                values = self.values
                queueLength = len(self.mainQueue)
                print(f"Searching for trades with {i}")
                for ind in items:
                    if self.selfTrades[0]["RAP"] < self.valuesJSON[str(ind["assetId"])]["correctedVal"] < \
                            self.selfTrades[-1]["RAP"]:
                        if self.valuesJSON[str(ind["assetId"])]["projected"] or values[str(ind["assetId"])][3] != -1:
                            inventoryArr.append(
                            {"UAID": ind["userAssetId"], "RAP": self.valuesJSON[str(ind["assetId"])]["correctedVal"],
                             "assetId": ind["assetId"]})
                            continue
                    if self.selfTrades[0]["RAP"] < values[str(ind["assetId"])][4] < self.selfTrades[-1]["RAP"]:
                        inventoryArr.append({"UAID": ind["userAssetId"], "RAP": self.valuesJSON[str(ind["assetId"])]["correctedVal"],
                                             "assetId": ind["assetId"]})
                        continue
                try:
                    canTrade = self.getReq(f"https://trades.roblox.com/v1/users/{i}/can-trade-with", self.cookies).json()
                    if not canTrade[
                        'canTrade']: continue
                except:
                    print(canTrade)
                    continue
                if not inventoryArr:
                    print("Empty inventory array", items)
                    print(self.selfTrades[-1]["RAP"], self.selfTrades[0]["RAP"])
                    continue
                # if i["upgrade"]:
                #    continue
                #    #upgrade code here
                # elif i["downgrade"]:
                #    continue
                #    #downgradecode here
                myTrades = self.selfTrades.copy()
                random.shuffle(myTrades)
                if len(inventoryArr) <= 3:
                    maxItems = len(inventoryArr)
                else:
                    maxItems = 4
                numberOfItems = random.randint(1, maxItems)
                allUAID = [x["UAID"] for x in inventoryArr]
                possibleTrades = list(combinations(allUAID, numberOfItems))
                for trade in possibleTrades:
                    trade = list(trade)
                    sendingFinal = {}
                    rapTotal = 0
                    UAIDs = trade
                    assetIDS = []
                    for item in trade:
                        for item2 in inventoryArr:
                            if int(item2["UAID"]) == int(item):
                                assetIDS.append(item2["assetId"])
                                rapTotal += item2['RAP']
                    finalTrade = {"UAIDs": [int(x) for x in list(np.sort(UAIDs))], "RAP": rapTotal, "assetIds": [int(x) for x in list(np.sort(assetIDS))]}
                    if rapTotal > maxTop4 or finalTrade in skipped: continue
                    if len(skipped) > 5: break
                    for trades in myTrades:
                        if trades["RAP"] * maxGain >= rapTotal >= trades["RAP"] * minGain:
                            sendingFinal = trades
                    if sendingFinal == {}:
                        print("No profit 0_0")
                        skipped.append(finalTrade)
                        continue
                    for asset in finalTrade["assetIds"]:
                        if not str(asset) in self.valuesJSON or self.valuesJSON[str(asset)]["correctedVal"] == 0:
                            time.sleep(1)
                            skipped.append(finalTrade)
                            finalTrade = {}
                            break
                    if finalTrade == {}:
                        continue
                    finalTrade["userID"] = i
                    self.mainQueue.append({"Sending": sendingFinal, "Receiving": finalTrade})
                    queueLength += 1
                    print(f"Queue length is now {queueLength}")
                    break
                # check each item, access item by "assetId" converted to string

    def sendCannon(self):
        counter = 0
        time.sleep(8)
        print("Sending trades...")
        while True:
            headers = {}
            if counter == 99:
                counter = 0
            while True:
                if self.mainQueue: break
                time.sleep(5)
            trade = self.mainQueue[0]
            proxyToUse = self.indvProxies[counter]
            headers = self.csrfTokensProxy[proxyToUse]
            proxyToUse = {"http": proxyToUse, "https": proxyToUse}
            UAIDs = []
            counter += 1
            for i in trade["Receiving"]["UAIDs"]:
                UAIDs.append(int(i))
            sending = []
            for i in trade["Sending"]["UAIDS"]:
                sending.append(int(i))
            if int(trade["Receiving"]["userID"]) in self.sentUsers:
                del self.mainQueue[0]
                continue
            payloadJSON = {"offers": [{"userId": int(trade["Receiving"]["userID"]), "userAssetIds": UAIDs, "robux": 0},
                                      {"userId": self.config["authentication"]["userId"], "userAssetIds": sending,
                                       "robux": 0}]}
            proxies = self.indvProxies
            tradeRes = self.postReq("https://trades.roblox.com/v1/trades/send", payloadJSON, headers, self.cookies,
                                    proxyToUse, True)
            if tradeRes.status_code == 200:
                print(f"SUCCESS, sent a trade to {trade['Receiving']['userID']}")
                tradeId = tradeRes.json()['id']
                self.outbound[tradeId] = {"Sending": trade["Sending"]["assetId"], "Receiving": trade['Receiving']['assetIds']}
                self.sentTrades.append({"offer": trade, "tradeId": tradeId})
                self.sentUsers.append(int(trade["Receiving"]["userID"]))
                del self.mainQueue[0]
            elif tradeRes.status_code == 429:
                print("Couldn't send due to rate limit")
            else:
                del self.mainQueue[0]
                print(tradeRes.json())
                print("Error while sending!")
            time.sleep(15)

    def centerPos(self, position):
        x = int(
            round(position[0] - (150 / 2))
        )
        y = int(
            round(position[1] - (150 / 2))
        )
        return (x, y)

    def getQueue(self):
        with open("queue.json", "r") as file:
            queueJson = json.load(file)
            if queueJson['expiration'] < time.time(): return
            self.mainQueue = queueJson['queue']

    def updateQueue(self):
        with open("queue.json", "w") as file:
            queueJson = {"queue": self.mainQueue, "expiration": self.nextQueueExpire}
            json.dump(queueJson, file)

    def generateImgs(self):
        myFont = ImageFont.truetype("Rubik-Medium.ttf", 25)
        with open("theme_setup.json", "r") as read_file:
            theme_setup = json.load(read_file)
        while True:
            while not self.sentTrades:
                time.sleep(5)
            trade = 0
            backgound = Image.open("background.jpeg").convert("RGBA")
            d = ImageDraw.Draw(backgound)
            self.updateRolis()
            values = self.values
            tradeId = self.sentTrades[trade]["tradeId"]
            sending = self.sentTrades[trade]["offer"]["Sending"]["assetId"]
            sendRAP = 0
            sendVal = 0
            receiving = self.sentTrades[trade]["offer"]["Receiving"]["assetIds"]
            receiveRAP = 0
            receiveVal = 0
            userId = self.sentTrades[trade]["offer"]["Receiving"]["userID"]
            imgArr = os.listdir("images")
            for i in range(len(sending)):
                assetId = sending[i]
                thing = ""
                if not f"{assetId}.jpeg" in imgArr:
                    thing = self.getReq(
                        f"https://thumbnails.roblox.com/v1/assets?assetIds={assetId}&returnPolicy=PlaceHolder&size=150x150&format=Jpeg&isCircular=false").json()
                    thing = self.getReq(thing["data"][0]["imageUrl"]).content
                    with open(f"images/{assetId}.jpeg", "wb") as file:
                        file.write(thing)
                    thing = Image.open(BytesIO(thing))
                else:
                    thing = Image.open(f"images/{assetId}.jpeg")
                sendRAP += values[str(assetId)][2]
                if not self.valuesJSON[str(assetId)]['projected']:
                    sendVal += values[str(assetId)][4]
                else:
                    sendVal += self.valuesJSON[str(assetId)]['correctedVal']
                if i == 0:
                    backgound.paste(thing, self.centerPos(theme_setup["give"]["item1"]["position"]))
                elif i == 1:
                    backgound.paste(thing, self.centerPos(theme_setup["give"]["item2"]["position"]))
                elif i == 2:
                    backgound.paste(thing, self.centerPos(theme_setup["give"]["item3"]["position"]))
                elif i == 3:
                    backgound.paste(thing, self.centerPos(theme_setup["give"]["item4"]["position"]))
            for i in range(len(receiving)):
                assetId = receiving[i]
                thing = ""
                if not f"{assetId}.jpeg" in imgArr:
                    thing = self.getReq(
                        f"https://thumbnails.roblox.com/v1/assets?assetIds={assetId}&returnPolicy=PlaceHolder&size=150x150&format=Jpeg&isCircular=false").json()
                    thing = self.getReq(thing["data"][0]["imageUrl"]).content
                    with open(f"images/{assetId}.jpeg", "wb") as file:
                        file.write(thing)
                    thing = Image.open(BytesIO(thing))
                else:
                    thing = Image.open(f"images/{assetId}.jpeg")
                receiveRAP += values[str(assetId)][2]
                if not self.valuesJSON[str(assetId)]['projected']: receiveVal += values[str(assetId)][4]
                else: receiveVal += self.valuesJSON[str(assetId)]['correctedVal']
                if i == 0:
                    backgound.paste(thing, self.centerPos(theme_setup["take"]["item1"]["position"]))
                elif i == 1:
                    backgound.paste(thing, self.centerPos(theme_setup["take"]["item2"]["position"]))
                elif i == 2:
                    backgound.paste(thing, self.centerPos(theme_setup["take"]["item3"]["position"]))
                elif i == 3:
                    backgound.paste(thing, self.centerPos(theme_setup["take"]["item4"]["position"]))
            d.text(theme_setup["drawn_text"]["rap_sent"]["position"], f"Sent RAP: {sendRAP}",
                   tuple(theme_setup["drawn_text"]["rap_sent"]["rgba"]), font=myFont)
            d.text(theme_setup["drawn_text"]["value_sent"]["position"], f"Sent Value: {sendVal}",
                   tuple(theme_setup["drawn_text"]["value_sent"]["rgba"]), font=myFont)
            d.text(theme_setup["drawn_text"]["rap_received"]["position"], f"Received RAP: {receiveRAP}",
                   tuple(theme_setup["drawn_text"]["rap_received"]["rgba"]), font=myFont)
            d.text(theme_setup["drawn_text"]["value_received"]["position"], f"Received Value: {receiveVal}",
                   tuple(theme_setup["drawn_text"]["value_received"]["rgba"]), font=myFont)
            d.text((10, 10), f"Trade sent to {userId}", (255, 255, 255, 255), font=myFont)
            backgound = backgound.convert("RGB")
            backgound.save(f"images/trades/{tradeId}.jpeg")
            del self.sentTrades[trade]

    def updateSing(self, proxy):
        headers = self.makenewCSRF(self.cookies, {"https": proxy, "http": proxy})
        self.csrfTokensProxy[proxy] = headers

    def updateProxyCSRF(self):
        with open("allProxies.json", "r") as file:
            self.indvProxies = json.load(file)['proxies']
        while True:
            print("Updating CSRF of Proxies...")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.updateSing, self.indvProxies)
            print("Done updating CSRFs")
            time.sleep(120)

    def checkInv(self):
        while True:
            thing = self.generateSelfTrade(self.config["authentication"]["userId"])
            self.selfTrades = thing
            time.sleep(120)

    def checkOutbounds(self):
        counter = 0
        while True:
            counter = 0
            #get pages and trade ids
            self.getOutbound()
            nextPage = ""
            outboundKeys = list(self.outbound.keys())
            outboundToCheck = []
            while nextPage is not None:
                trades = self.getReq(f"https://trades.roblox.com/v1/trades/outbound?cursor={nextPage}&limit=100&sortOrder=Desc", self.cookies).json()
                print(trades)
                nextPage = trades["nextPageCursor"]
                for i in trades['data']:
                    if i['id'] not in outboundKeys:
                        outboundToCheck.append(i['id'])
            #Get each outbound that isn't in json
            print(outboundToCheck)
            for i in outboundToCheck:
                time.sleep(1)
                sending = []
                receiving = []
                trade = self.getReq(f"https://trades.roblox.com/v1/trades/{i}",self.cookies).json()['offers']
                for item in trade[0]['userAssets']:
                    sending.append(item['assetId'])
                for item in trade[1]['userAssets']:
                    receiving.append(item['assetId'])
                self.outbound[i] = {"Sending": sending, "Receiving": receiving}
            #Actual check
            outboundKeys = list(self.outbound.keys())
            self.updateRolis()
            for i in outboundKeys:
                if counter == 99:
                    counter = 0
                counter += 1
                proxyToUse = self.indvProxies[counter]
                sendingTotal = 0
                receiveTotal = 0
                for item in self.outbound[i]["Sending"]:
                    if self.valuesJSON[str(item)]["projected"] or self.values[str(item)][3] == -1:
                        sendingTotal += self.valuesJSON[str(item)]["correctedVal"]
                    else:
                        sendingTotal += self.valuesJSON[str(item)]["actualVal"]
                for item in self.outbound[i]["Receiving"]:
                    if self.valuesJSON[str(item)]["projected"] or self.values[str(item)][3] == -1:
                        receiveTotal += self.valuesJSON[str(item)]["correctedVal"]
                    else:
                        receiveTotal += self.valuesJSON[str(item)]["actualVal"]
                if sendingTotal > receiveTotal:
                    csrf = self.csrfTokensProxy[proxyToUse]
                    self.postReq(f"https://trades.roblox.com/v1/trades/{i}/decline", {}, csrf, self.cookies, proxyToUse)
                    print(f"Declined trade {i}")
                    del self.outbound[i]
            self.updateOutbound()
            time.sleep(120)




    def main(self):
        self.getValues()
        scrapeT = threading.Thread(target=self.scrapeMain)
        scrapeT.start()
        time.sleep(15)
        # problem!! down here
        thing = self.generateSelfTrade(self.config["authentication"]["userId"])
        self.selfTrades = thing
        thread = threading.Thread(target=self.sendCannon)
        imgT = threading.Thread(target=self.generateImgs)
        proxyT = threading.Thread(target=self.updateProxyCSRF)
        checkT = threading.Thread(target=self.checkInv)
        outT = threading.Thread(target=self.checkOutbounds)
        thread.start()
        imgT.start()
        proxyT.start()
        checkT.start()
        outT.start()
        self.generateQueue()


# 4 is rap/value
# 6 is the trend
# 2 is stable, 0 is lowering, 1 is unstable

# Ropro: -4 is upgrade, -5 is downgrade
myTradeBot = tradeBot()
myTradeBot.main()
