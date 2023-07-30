# osu-beatmap-downloader

[![Actions Status](https://github.com/segalll/osu-beatmap-downloader/workflows/CI/badge.svg)](https://github.com/segalll/osu-beatmap-downloader/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Downloads missing [osu!](https://osu.ppy.sh/home) beatmapsets in bulk.

## Usage
### Download Python 3 (if necessary)
https://www.python.org/downloads/
### Get the code
```
git clone https://github.com/segalll/osu-beatmap-downloader
cd osu-beatmap-downloader
```

### Register an osu! OAuth application
https://osu.ppy.sh/home/account/edit#oauth


Create a file in the same directory as this script called `.env` with the following contents:
```
CLIENT_ID=<your OAuth client id>
CLIENT_SECRET=<your OAuth client secret>
```

### Install dependencies
```
pip install -r requirements.txt
```

### Running
```
python beatmapdownloader.py
```

Search queries work like the in-game search interface. Valid filters can be found under the Search section of https://osu.ppy.sh/wiki/en/Client/Interface