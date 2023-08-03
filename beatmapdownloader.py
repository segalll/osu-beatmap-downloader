#!/usr/bin/env python3

from dotenv import dotenv_values
from ossapi import (
    Ossapi,
    BeatmapsetSearchMode,
    BeatmapsetSearchCategory,
    BeatmapsetSearchExplicitContent,
)
from tqdm import tqdm
import requests

from multiprocessing.pool import ThreadPool
import os
import re
import sys
import time
import tkinter.filedialog
import urllib


def get_search_query() -> str:
    return input("Please enter a search query: ")


def get_songs_dir() -> str:
    print("\nPlease select your osu! Songs directory")
    songs_dir = tkinter.filedialog.askdirectory(
        initialdir="./", mustexist=True, title="Select your osu! Songs directory"
    )
    if songs_dir.split("/")[-1] != "Songs":
        sys.exit("Selected directory is not the osu! Songs directory")
    return songs_dir


def get_downloaded_mapsets(songs_dir: str) -> set[int]:
    downloaded_mapsets = set(
        [
            int(f.name.split(" ")[0])
            for f in os.scandir(songs_dir)
            if f.is_dir() and f.name.split(" ")[0].isdigit()
        ]
    )
    print("Scanned %s\n" % songs_dir)
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
    with tqdm(initial=len(sets), total=r.total, desc="Downloading map list") as pbar:
        while len(sets) < r.total:
            r = api.search_beatmapsets(
                query,
                mode=BeatmapsetSearchMode.OSU,
                category=BeatmapsetSearchCategory.HAS_LEADERBOARD,
                explicit_content=BeatmapsetSearchExplicitContent.SHOW,
                cursor=r.cursor,
            )
            sets += r.beatmapsets
            pbar.update(len(r.beatmapsets))
    return set([s.id for s in sets])


def get_missing_mapsets(downloaded: set[int], all: set[int]) -> list[int]:
    return sorted(all.difference(downloaded))


def get_delta_time_ms() -> int:
    global g_start_time
    return round((time.time() - g_start_time) * 1000.0)


def download_mapset(mapset_id_and_songs_dir: tuple[int, str]) -> tuple[int, bool]:
    mapset_id, songs_dir = mapset_id_and_songs_dir
    r = requests.get("https://api.chimu.moe/v1/download/%d" % mapset_id, stream=True)
    if r.headers["Content-Type"] != "application/octet-stream":
        return mapset_id, False
    d = r.headers["Content-Disposition"]
    filename = urllib.parse.unquote(d.split("filename=")[1])
    filename = re.sub(r'[\/\\\*:\?"\<>\|]', "", filename)
    with open(os.path.join(songs_dir, filename), "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)
    return mapset_id, True


def download_missing_mapsets(missing_mapsets: list[int], songs_dir: str) -> list[int]:
    pool = ThreadPool(16)
    combined_data = [(mapset_id, songs_dir) for mapset_id in missing_mapsets]
    failed_maps = []
    for id, success in tqdm(pool.imap_unordered(download_mapset, combined_data), total=len(combined_data), desc="Downloading mapsets"):
        if not success:
            failed_maps.append(id)
    return failed_maps


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
