import requests
import os
import urllib
import datetime
import re

def getDownloadedBeatmaps():
    maps = set([int(f.name.split(" ")[0]) for f in os.scandir("../Songs/") if f.is_dir() and f.name.split(" ")[0].isdigit()])
    print("\nScanned songs folder\n")
    return maps

def getAllBeatmaps(key, date):
    maps = []
    newMapLen = 500
    while newMapLen == 500: # request yields 500 results until we run out of maps to fetch
        response = requests.get("https://osu.ppy.sh/api/get_beatmaps?k=%s&m=0&since=%s" % (key, date))
        newMaps = response.json()
        newMapLen = len(newMaps)
        maps += newMaps
        lastMap = newMaps[-1]
        date = lastMap["approved_date"]
        print('Downloading map list... [maps: {:d}]'.format(len(maps)), end='\r')
    print('Downloaded map list... [maps: {:d}]\n'.format(len(maps)))
    return maps

def filterAllBeatmaps(maps, status, starsFilter): # status is 4 = loved, 3 = qualified, 2 = approved, 1 = ranked, 0 = pending, -1 = WIP, -2 = graveyard
    print("Filtered beatmaps")
    if starsFilter == "n":
        return set([int(m["beatmapset_id"]) for m in maps if int(m["approved"]) in status])
    elif starsFilter[0] == "<=":
        return set([int(m["beatmapset_id"]) for m in maps if int(m["approved"]) in status and float(m["difficultyrating"]) <= starsFilter[1]])
    else:
        return set([int(m["beatmapset_id"]) for m in maps if int(m["approved"]) in status and float(m["difficultyrating"]) >= starsFilter[1]])

def getMissingBeatmaps(downloaded, all):
    return sorted(all.difference(downloaded))

def downloadMissingBeatmaps(missing):
    i = 1
    for m in missing:
        r = requests.get("https://chimu.moe/d/%d" % m, stream=True)
        if r.headers["Content-Type"] != "application/octet-stream":
            print("%s failed, please download manually" % m)
            i += 1
            continue
        d = r.headers["Content-Disposition"]
        filename = urllib.parse.unquote(d.split('filename="')[1].split('";')[0]).replace("/", "_").replace("\"", "")
        with open("..\\Songs\\%s" % filename, "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)
        print("Downloaded %s (%s/%s)" % (filename, i, len(missing)))
        i += 1
    print("\nDownloads complete")

def apiKeyIsValid(apiKey):
    response = requests.get("https://osu.ppy.sh/api/get_beatmaps?k=%s&m=0&limit=1" % apiKey)
    if "error" in response.json():
        return False
    else:
        return True

def getApiKey():
    if os.path.exists("api_key"):
        apiKey = open("api_key", "r").read()
        if apiKeyIsValid(apiKey):
            return apiKey
        else:
            print("The api key in your api_key file is invalid, switching to manual input.")
    while True:
        apiKey = input("Please enter your api key: ")
        if not apiKeyIsValid(apiKey):
            print("Invalid api key entered. Try again.")
            continue
        else:
            open("api_key", "w").write(apiKey)
            return apiKey

def getDate():
    while True:
        year = input("\nPlease enter the year you want to begin fetching maps from (i.e. if you input 2019, you will download maps approved during or after 2019): ")
        if not year.isdigit() or int(year) > datetime.datetime.now().year or int(year) < 0:
            print("Invalid year entered. Try again.")
            continue
        else:
            return "%s-01-01" % year

def shouldDownloadApprovedStatus(approvedStatus):
    while True:
        approved = input("Would you like to download %s maps? (y/n): " % approvedStatus)
        if approved != "y" and approved != "n":
            print("Invalid input entered. Try again.")
            continue
        else:
            return True if approved == "y" else False 

def getApprovedList():
    ranked = shouldDownloadApprovedStatus("ranked")
    approved = shouldDownloadApprovedStatus("approved")
    qualified = shouldDownloadApprovedStatus("qualified")
    loved = shouldDownloadApprovedStatus("loved")
    approvedList = []
    if ranked:
        approvedList.append(1)
    if approved:
        approvedList.append(2)
    if qualified:
        approvedList.append(3)
    if loved:
        approvedList.append(4)
    return approvedList

def getStarsFilter():
    while True:
        filterType = input("Filter star rating (>=, <=, n for none): ")
        if filterType != ">=" and filterType != "<=" and filterType != "n":
            print("Invalid input entered. Try again.")
            continue
        else:
            if filterType == "n":
                return filterType
            while True:
                stars = input("Stars %s: " % filterType)
                if re.match(r'^-?\d+(?:\.\d+)?$', stars) is None:
                    print("Invalid input entered. Try again.")
                    continue
                else:
                    return (filterType, float(stars))

apiKey = getApiKey()
date = getDate()
approvedList = getApprovedList()
starsFilter = getStarsFilter()
downloadedMaps = getDownloadedBeatmaps()
allMaps = getAllBeatmaps(apiKey, date)
filteredMaps = filterAllBeatmaps(allMaps, approvedList, starsFilter)
missingMaps = getMissingBeatmaps(downloadedMaps, filteredMaps)
downloadMissingBeatmaps(missingMaps)
