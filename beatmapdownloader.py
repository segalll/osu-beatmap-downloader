import requests
import os
import urllib
import datetime
import re
import unicodedata
import threading
import time

from enum import Enum
from multiprocessing.dummy import Pool as ThreadPool

g_pool = ThreadPool(16)
g_threadLock = threading.Lock()
g_start = time.time()

# To set later
g_beatmapsCounter = 0
g_beatmapsTotal = 0

class OsuMode(Enum):
    OSU       = 0
    OSU_TAIKO = 1
    OSU_CTB   = 2
    OSU_MANIA = 3

def get_milli_delta_time():
    global g_start
    return round((time.time() - g_start) * 1000.0)

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def getDownloadedBeatmaps():
    maps = set([int(re.split(r'\D+', f.name)[0]) for f in os.scandir("../Songs/") if f.is_dir() and re.split(r'\D+', f.name)[0].isdigit()])
    print("\nScanned songs folder - (%d songs scanned)\n" % (len(maps),))
    return maps

def getAllBeatmaps(key, date, mode=0):
    """
    mode -> 0:OSU, 1:TAIKO, 2:CTB, 3:OSU_MANIA
    """
    maps = []
    newMapLen = 500
    while newMapLen == 500: # request yields 500 results until we run out of maps to fetch
        response = requests.get("https://osu.ppy.sh/api/get_beatmaps?k=%s&m=%d&since=%s" % (key, mode, date))
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

def downloadSingleBeatmap(m):
    global g_beatmapsCounter
    global g_beatmapsTotal
    global g_threadLock

    r = requests.get("https://chimu.moe/d/%d" % m, stream=True)
    if r.headers["Content-Type"] != "application/octet-stream":
        print("%s failed, please download manually" % m)
        with g_threadLock:
            g_beatmapsCounter += 1
        return m
    d = r.headers["Content-Disposition"]
    filename = slugify(urllib.parse.unquote(d.split('filename="')[1].split('";')[0]))
    if filename.endswith("osz") and filename[-4] != ".":
        filename = filename[:-4] + ".osz"
    else:
        filename = filename + ".osz"
    with open("..\\Songs\\%s" % filename, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)
    delta = get_milli_delta_time()
    with g_threadLock:
        print("[%d ms] Downloaded %s (%s/%s)" % (delta, filename, g_beatmapsCounter, g_beatmapsTotal))
        g_beatmapsCounter += 1
    return m

def downloadMissingBeatmaps(missing):
    global g_beatmapsCounter
    global g_beatmapsTotal
    global g_pool

    g_beatmapsCounter = 1
    g_beatmapsTotal = len(missing)
    list(g_pool.imap_unordered(downloadSingleBeatmap, list(missing)))
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

def getOsuMode():
    while True:
        osu_mode = input("Osu mode (0 -> osu, 1 -> taiko, 2 -> CtB, 3 -> osu!mania): ")
        if osu_mode.lower() not in set(["osu", "taiko", "ctb", "mania", "osu!mania", "0", "1", "2", "3"]):
            print("Invalid input enetered. Try again.")
            continue
        else:
            if osu_mode.isdigit():
                return int(osu_mode)
            else:
                return {
                    "osu": 0,
                    "taiko": 1,
                    "ctb": 2,
                    "mania": 3,
                    "osu!mania": 3
                }[osu_mode]

def work():
    apiKey = getApiKey()
    date = getDate()
    approvedList = getApprovedList()
    starsFilter = getStarsFilter()
    osu_mode = getOsuMode()
    downloadedMaps = getDownloadedBeatmaps()
    allMaps = getAllBeatmaps(apiKey, date, osu_mode)
    filteredMaps = filterAllBeatmaps(allMaps, approvedList, starsFilter)
    missingMaps = getMissingBeatmaps(downloadedMaps, filteredMaps)
    downloadMissingBeatmaps(missingMaps)

if __name__ == "__main__":
    work()
