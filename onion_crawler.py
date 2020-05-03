import atexit
import collections
import csv
import gzip
import os.path
import sys
import socks
import socket
import re
import requests
import time

from bs4 import BeautifulSoup as soup 
from os import path
from urllib.parse import urljoin
from urllib3.util.retry import Retry

url_count = 0
prefixes = ("href=\"", "<li>", "<ul><li>", "\"", "<s>", "href=\'", 
            "action=\"", "src=\'", "src=\"", "target=", "href=",
            "value=\", content=\"", "title=\"", "rel=", "<h1>",
            "<title>", "valign=\"top\"", "<center>", "content=\'",
            "value=\"")

media_suffixes = (".jpg", ".jpeg", ".png", ".gif", 
                  ".webm", ".pdf", ".mp3", ".ico")

clearnet_suffixes = (".com", ".net", ".org", 
                    ".co", ".gov", ".com.au",
                    ".de, .us")
content_types = ("audio/mpeg", "video/webm", "video/mpeg", "video/mp4")
removed_prefix = False
url_valid = False

session = requests.session()
session.proxies = ({'http':  'socks5h://127.0.0.1:9150',
                    'https': 'socks5h://127.0.0.1:9150'})

#error checking args
if len(sys.argv) is 1:
    print("Enter .onion URL. Add -r at the end to re-crawl previous live urls or -d for previous dead urls.")
    exit()
if len(sys.argv) > 3:
    print("Invalid arguments.")
    exit()

if not ".onion" in sys.argv[1]:
    print("Only use .onion links.")
    exit()

#adding first url to set & queue
url_queue = collections.deque()
url_queue.append(sys.argv[1])

found = set()
found.add(sys.argv[1])
links = set()
file_urls = set()

#add urls from files
if len(sys.argv) is 3:
    if(sys.argv[2] == "-r"):
        with open('urls_working.csv', newline='') as f:
            live_reader = csv.reader(f)
            live_data = list(live_reader)
        
        for item in live_data:
            if item is not None and item:
                url_queue.append(item[0])

    if(sys.argv[2] == "-d"):
        with open('urls_dead.csv', newline='') as f:
            dead_reader = csv.reader(f)
            dead_data = list(dead_reader)

        for item in dead_data:
            if item is not None and item:
                url_queue.append(item[0])

url_files = input("Would you like to save file URLs (images, audio, pdfs)? y/n ")

#file creation
filename1 = "urls_working.csv"
filename2 = "urls_dead.csv"
filename3 = "urls_files.csv"
filename4 = "urls_progress.txt"

if not path.exists(filename1):
    headers = "url, title\n"
else:
    headers = ""

f = open(filename1, "a")
f.write(headers)

if not path.exists(filename2):
    headers = "url, error\n"
else:
    headers = ""

f2 = open(filename2, "a")
f2.write(headers)

if not path.exists(filename3):
    headers = "url\n"
else:
    headers = ""

f3 = open(filename3, "a")
f3.write(headers)

f4 = open(filename4, "r+")

for line in f4:
    links.add(line)
f4.truncate(0)

#save links if program exit
def save_list():
    for link in links:
        f4.write(link + "\n")
    f.close()
    f2.close()
    f3.close()
    f4.close()

atexit.register(save_list)

#main loop
while len(url_queue):
    url = url_queue.popleft()

    if ".onion" not in url:
        continue

    url = url.strip('\'"')
    url = url.rstrip()

    if "http" not in url and "https" not in url:
        url = "http://" + url
    print("\nTrying URL: " + url)

    try:
        r = session.get(url, headers={"User-Agent":"Mozzila/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0"}, 
                        timeout=10)

        if any(ext in r.headers.get("Content-Type", '') for ext in content_types):
            url_valid = False
            f.write(url + ", " + "Audio/Video Stream" + "\n")
        else:
            page_html = r.text
            url_valid = True
            print("URL Valid. Scraping ... Please Wait.")
    except Exception as e:
        print("URL Invalid. Error: " + str(e))
        f2.write(url + ", " + str(e).replace(",", "+") + "\n")
        url_valid = False
        
    if url_valid is True:
        page_soup = soup(page_html, "html.parser")

        if page_soup.title is None:
            title = "<NO TITLE>"
        else:
            title = page_soup.title.string

        f.write(url + ", " + title.replace(",", "|") + "\n")
        print("URL Title: " + title.replace(",", "|") + "\n")

        #page soup href's
        for link in page_soup.find_all('a', href=True):
            if link['href'].endswith(media_suffixes):
                if url_files is 'y':
                    if ".onion" not in link['href']:
                        joined = urljoin(url, link['href'])
                        if joined not in file_urls:
                            file_urls.add(joined)
                            f3.write(joined + "\n")
                    else:
                        file_urls.add(link['href'])
                        f3.write(urljoin(url, link['href']) + "\n")
                continue
            
            if ".onion" not in link['href']:
                links.add(urljoin(url, link['href']))
            else:
                links.add(link['href'])

        #page soup img src
        if url_files is 'y':
            for img_link in page_soup.find_all('img'):
                img_link = urljoin(url, img_link['src'])
                if img_link not in file_urls:
                    file_urls.add(img_link)
                    f3.write(img_link +"\n")

        #findall .onion regex
        for string in re.findall('\S+\.onion[^\s<>"]+', page_html):
            if ".js" in string:
                continue
            if ".css" in string:
                continue
            if "irc://" in string:
                continue
            if "gopher://" in string:
                continue

            if string.endswith(media_suffixes):
                if url_files is 'y' and string not in file_urls:
                    file_urls.add(string)
                    f3.write(string + "\n")
                continue

            for prefix in prefixes:
                if string.startswith(prefix):
                    clean_string = string[len(prefix):]
                    clean_string = clean_string.split('"',1)[0]
                    clean_string = clean_string.split('<',1)[0]
                    clean_string = clean_string.split('>',1)[0]
                    links.add(clean_string)
                    removed_prefix = True
                    break
            if removed_prefix is False:   
                links.add(string)

            removed_prefix = False

        for link in (links - found):
            found.add(link)
            url_queue.append(link)
            url_count = url_count + 1

        if len(url_queue):
            for remaining in range(5, 0, -1):
                sys.stdout.write("\r")
                sys.stdout.write("{:2d} seconds until next URL".format(remaining))
                sys.stdout.flush()
                time.sleep(1)

links.clear()
print("\n\nURLs found: " + str(url_count))