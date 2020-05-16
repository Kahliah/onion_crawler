## .onion crawler
Crawls .onion urls, scrapes urls on the site and visits them, the sites url and title will be archived to a file. If url is invalid/site down then that will be archived to another file. Optionally, images can be scraped and archived with their url to another file.

# Use
Run the script with `python onion_crawler onionurlyouwantcrawled.onion`
Use -r to re-crawl the previous valid urls, and -d for previous dead urls.
Must have Tor Browser open while doing this, or if you are using the service, change lines 36-37 to `9050`

Will only crawl urls that contain .onion
