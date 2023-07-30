#!/usr/bin/env python3

from dotenv import dotenv_values
from ossapi import (
    Ossapi,
    BeatmapsetSearchMode,
    BeatmapsetSearchCategory,
    BeatmapsetSearchExplicitContent,
)

from multiprocessing.pool import ThreadPool
import os
import re
import requests
import sys
import threading
import time
import tkinter.filedialog
import urllib


g_thread_lock = threading.Lock()

# To set later
g_beatmapset_counter = 0
g_beatmapset_total = 0
g_start_time = 0


def get_search_query() -> str:
    return input("Please enter a search query: ")


def get_songs_dir() -> str:
    print("\nPlease select your osu! Songs directory")
    songs_dir = tkinter.filedialog.askdirectory(
        initialdir="./", mustexist=True, title="Select your osu! Songs directory"
    )
    if songs_dir.split("/")[-1] != "Songs":
        sys.exit("\nSelected directory is not the osu! Songs directory")
    return songs_dir


def get_downloaded_mapsets(songs_dir: str) -> set[int]:
    downloaded_mapsets = set(
        [
            int(f.name.split(" ")[0])
            for f in os.scandir(songs_dir)
            if f.is_dir() and f.name.split(" ")[0].isdigit()
        ]
    )
    print("\nScanned %s\n" % songs_dir)
    return downloaded_mapsets


def get_desired_mapsets(query: str) -> set[int]:
    config = dotenv_values(".env")
    if "CLIENT_ID" not in config:
        sys.exit("\n.env config missing CLIENT_ID setting")
    if "CLIENT_SECRET" not in config:
        sys.exit("\n.env config missing CLIENT_SECRET setting")

    api = Ossapi(int(config["CLIENT_ID"]), config["CLIENT_SECRET"])
    r = api.search_beatmapsets(
        query,
        mode=BeatmapsetSearchMode.OSU,
        category=BeatmapsetSearchCategory.HAS_LEADERBOARD,
        explicit_content=BeatmapsetSearchExplicitContent.SHOW,
    )
    sets = r.beatmapsets
    while len(sets) < r.total:
        r = api.search_beatmapsets(
            query,
            mode=BeatmapsetSearchMode.OSU,
            category=BeatmapsetSearchCategory.HAS_LEADERBOARD,
            explicit_content=BeatmapsetSearchExplicitContent.SHOW,
            cursor=r.cursor,
        )
        sets += r.beatmapsets
        print(
            "Downloading map list... [{:d}/{:d}]".format(len(sets), r.total),
            end="\r",
        )
    return set([s.id for s in sets])


def get_missing_mapsets(downloaded: set[int], all: set[int]) -> list[int]:
    return sorted(all.difference(downloaded))


def get_delta_time_ms() -> int:
    global g_start_time
    return round((time.time() - g_start_time) * 1000.0)


def download_mapset(mapset_id_and_songs_dir: tuple[int, str]) -> tuple[int, bool]:
    global g_beatmapset_counter
    global g_beatmapset_total
    global g_thread_lock

    mapset_id, songs_dir = mapset_id_and_songs_dir
    r = requests.get("https://api.chimu.moe/v1/download/%d" % mapset_id, stream=True)
    if r.headers["Content-Type"] != "application/octet-stream":
        print("%s failed, please download manually" % mapset_id)
        with g_thread_lock:
            g_beatmapset_counter += 1
        return mapset_id, False
    d = r.headers["Content-Disposition"]
    filename = urllib.parse.unquote(d.split("filename=")[1])
    filename = re.sub(r'[\/\\\*:\?"\<>\|]', "", filename)
    with open(os.path.join(songs_dir, filename), "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)
    with g_thread_lock:
        print(
            "[%d ms] Downloaded %s (%s/%s)"
            % (get_delta_time_ms(), filename, g_beatmapset_counter, g_beatmapset_total)
        )
        g_beatmapset_counter += 1
    return mapset_id, True


def download_missing_mapsets(missing_mapsets: list[int], songs_dir: str) -> list[int]:
    global g_beatmapset_counter
    global g_beatmapset_total
    global g_start_time

    g_start_time = time.time()
    g_beatmapset_counter = 1
    g_beatmapset_total = len(missing_mapsets)

    pool = ThreadPool(16)
    combined_data = [(mapset_id, songs_dir) for mapset_id in missing_mapsets]
    map_results = list(pool.imap_unordered(download_mapset, combined_data))
    print("\nDownloads complete")
    return [id for id, success in map_results if not success]


def main():
    query = get_search_query()
    songs_dir = get_songs_dir()
    downloaded_mapsets = get_downloaded_mapsets(songs_dir)
    desired_mapsets = get_desired_mapsets(query)
    missing_mapsets = get_missing_mapsets(downloaded_mapsets, desired_mapsets)
    need_manual_download = download_missing_mapsets(missing_mapsets, songs_dir)
    if len(need_manual_download) > 0:
        print("\nThe following mapsets require manual download:")
        for m in need_manual_download:
            print("https://osu.ppy.sh/beatmapsets/%d" % m)


if __name__ == "__main__":
    main()
