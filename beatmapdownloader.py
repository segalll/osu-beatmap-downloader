import time
import urllib.request
import json
import os
import hashlib
import collections
from requests import session
import sys
from bs4 import BeautifulSoup
import re
import datetime
import time
import requests

rankedconfig = None
lovedconfig = None

def get_year():
    while(True):
        inputstuff = input('Enter the year you want your maps to be from (for example, if you want all maps made during or after 2017, type 2017): ')
        if not inputstuff.isdigit():
            print('Invalid input')
        elif int(inputstuff) < 2007 or int(inputstuff) > datetime.datetime.now().year:
            print('Input not within valid years (2007 - %s)' % datetime.datetime.now().year)
        else:
            return inputstuff

def get_approval_config(config):
    while(True):
        userinput = input('Do you want all %s maps (type yes or no)?: ' % config)
        if userinput == 'yes':
            return True
        elif userinput == 'no':
            return False
        else:
            print('Invalid input.')
            
def get_approval_things():
    while(True):
        rankedconfig = get_approval_config('ranked')
        lovedconfig = get_approval_config('loved')
        if (not rankedconfig) and (not lovedconfig):
            print('You must answer yes to at least one of these.')
        else:
            return
            
def get_next_date(ordered_dict):
    bm_key = next(reversed(ordered_dict))
    bm = ordered_dict[bm_key]
    date_str = (bm['approved_date'].split(' '))[0]
    return datetime.datetime.strptime(date_str, date_format)
 
def get_page(key, date):
    url_base = 'https://old.ppy.sh/api/get_beatmaps?'
    url = url_base + 'k=' + key + '&since=' + date.strftime(date_format) + '&m=0'
    page = urllib.request.urlopen(url)
    return page.read()
 
def get_api_key():
    print('The api key can be found at https://osu.ppy.sh/p/api')
    api_key = input('Key: ')
    try:
        test = get_page(api_key, page_date)
    except urllib.error.HTTPError:
        print('That key is invalid, try again.')
        return get_api_key()
    return api_key
 
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

print("You are about to be asked to input your username and password. This is used to get through the verification on the website.")
usernameosu = input('Enter your osu username: ')
passwordosu = input('Enter your osu password: ')
get_approval_things()
authentication_url = 'https://old.ppy.sh/forum/ucp.php'
yearthing = get_year()
start_date_stamp = '%s-10-07' % yearthing
date_format = '%Y-%m-%d'
page_date = datetime.datetime.strptime(start_date_stamp, date_format)
api_key = ''
db = {}
if os.path.isfile('missing_maps.txt'):
    os.remove('missing_maps.txt')

if os.path.isfile('md5_mtime_db'):
    os.remove('md5_mtime_db')

if os.path.isfile('map_list.json'):
    os.remove('map_list.json')

payload = {
    'action': 'login',
    'username': usernameosu,
    'password': passwordosu,
    'redirect': 'index.php',
    'sid': '',
    'login': 'Login'
}
missing_maps = []
download_url = 'https://old.ppy.sh/d/'
TAG_RE = re.compile(r'<[^>]+>')

# Get API key
if os.access('api_key', os.F_OK):
    with open('api_key', 'r') as key_file:
        api_key = key_file.readline().strip()
else:
    api_key = get_api_key()
    with open('api_key', 'w') as key_file:
        key_file.write(api_key)
 
# Get md5/mtime db
if os.access('md5_mtime_db', os.F_OK):
    with open('md5_mtime_db', 'r') as mmdb:
        db = json.loads(mmdb.read())
       
walk = next(os.walk(os.path.join(os.path.dirname(__file__), os.pardir, 'Songs')))
dirs = walk[1]
path = walk[0]
md5s = {}
for i, d in enumerate(dirs):
    print('Scanning songs folder... [maps: {:d} ({:.2f}%)]'.format(len(md5s), (i/len(dirs)) * 100), end='\r')
    dir_path = os.path.join(path, d)
    files = next(os.walk(dir_path))[2]
    for f in files:
        if f[-3:] == 'osu':
            rel_path = os.path.join(d, f)
            abs_path = os.path.join(dir_path, f)
            f_mtime = os.path.getmtime(abs_path)
            if (rel_path in db) and (db[rel_path][0] == f_mtime):
                md5s[db[rel_path][1]] = None
            else:
                f_md5 = md5(abs_path)
                md5s[f_md5] = None
                db[rel_path] = (f_mtime, f_md5)
 
with open('md5_mtime_db', 'w') as mmdb:
    mmdb.write(json.dumps(db))
           
print('Scanning songs folder... [maps: {:d} (100%)]  '.format(len(md5s)))
 
# Get a dictionary of all ranked standard maps
if os.access('map_list.json', os.F_OK):
    with open('map_list.json', 'r') as rmj:
        maps = collections.OrderedDict(json.loads(rmj.read()))
        page_date = get_next_date(maps)
else:
    maps = collections.OrderedDict([])
 
num_maps = -1
 
while (num_maps != len(maps)):
    num_maps = len(maps)
    print('Downloading map list... [maps: {:d}]'.format(num_maps), end='\r')
    page = get_page(api_key, page_date)
    parsed_page = json.loads(page)
    for bm in parsed_page:
        if bm['approved'] != '3':
            maps[bm['file_md5']] = bm
   
    page_date = get_next_date(maps)
    time.sleep(1.1)
 
print('Downloading map list... [maps: {:d}]'.format(num_maps))
 
with open('map_list.json', 'w') as rmj:
    rmj.write(json.dumps(maps))
 
# Generate a set of all mapsets that are not present
missing = {}
ranked = 0
loved = 0
errors = 0
 
for key in maps:
    if maps[key]['approved'] == '4':
        if lovedconfig == True:
            loved += 1
    elif maps[key]['approved'] in ('1', '2'):
        if rankedconfig == True:
            ranked += 1
    else:
        errors += 1
    if key not in md5s:
        missing[maps[key]['beatmapset_id']] = None
 
print('Map composition:')

if rankedconfig == True:
    print('    Ranked:  ' + str(ranked))
if lovedconfig == True:
    print('    Loved:   ' + str(loved))
print('    Unknown: ' + str(errors))
 
if len(missing.keys()) == 0:
    print('All maps accounted for.')
else:
    print('Missing maps by song id:')
    with open('missing_maps.txt', 'w') as stuff:
        for key in missing.keys():
            print(key)
            missing_maps.append(key)
            stuff.write(key)
            stuff.write('\n')

with session() as c:
    c.post(authentication_url, data=payload)
    def download_beatmaps(url, proxies, countthing, proxynum):
        proxy = urllib.request.ProxyHandler({'http': proxies[proxynum]})
        opener = urllib.request.build_opener(proxy)
        urllib.request.install_opener(opener)
        print('Using IP ' + proxies[proxynum])
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0")
        r = urllib.request.urlopen(req)
        soup = BeautifulSoup(r, "html5lib")
        partname = soup.find('title')
        filename = url_split(url) + ' ' + remove_tags(partname) + ".osz"
        print(filename)
        print('Downloading...')
        r = c.get(download_url(url), stream=True)
        usedfilename = os.path.join(os.path.dirname(__file__), os.pardir, 'Songs', filename)
        with open(usedfilename, 'wb') as beatmap:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk: # filter out keep-alive new chunks
                    if chunk == 'slow done, play more':
                        print('You have reached the download limit set by the osu! website for now. Try again later.')
                        return
                    else:
                        beatmap.write(chunk)
            beatmap.close()
            print('Download completed')

    def remove_tags(text):
        partname = TAG_RE.sub('', text.text)
        title = re.sub('[\/*?:<>"|]', '', partname)
        otherthing = title.split(" (mapped")
        return otherthing[0]

    def url_split(url):
        return url.rsplit('/', 1)[-1]

    def download_url(url):
        new_url = url.rsplit('/', 2)[-3] + "/d/" + url.rsplit('/', 1)[-1]
        print(new_url)
        return new_url

    def new_download_url(url):
        r = c.get(url)
        soup = BeautifulSoup(r.content, "html5lib")
        new_url_part = soup.find('a', class_='beatmap_download_link')
        new_url = ('https://old.ppy.sh'+ new_url_part['href'])
        return new_url

    def difficulty():
        if difficulty_no == 0: return 'Beginner'
        elif difficulty_no == 1: return 'Standard'
        elif difficulty_no == 2: return 'Expert'

    def run():   
        proxies = re.findall(r'[0-9]+(?:\.[0-9]+){3}:[0-9]+', requests.get('https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt').text)
        countthing = 0
        proxynum = 0
        for i in range(0, len(missing_maps) - 1):
            url = 'https://old.ppy.sh/s/' + missing_maps[i]
            download_beatmaps(url, proxies, i, proxynum)
            i += 1
            if i > 75:
                proxynum += 1
                if proxynum > len(proxies) - 1:
                    proxynum -= len(proxies)
            time.sleep(5)

def main():
    starttime = datetime.datetime.now()
    run()
    endtime = datetime.datetime.now()
    print('Downloads have finished! Duration: %s' % str(endtime - starttime))
    if os.path.isfile('missing_maps.txt'):
        os.remove('missing_maps.txt')

    if os.path.isfile('md5_mtime_db'):
        os.remove('md5_mtime_db')

    if os.path.isfile('map_list.json'):
        os.remove('map_list.json')

if __name__ == "__main__":
    main()