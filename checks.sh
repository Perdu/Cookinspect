#!/bin/bash

# Simple script to make some tests when a campaign is running

LOG_FILES="logs_AC_2020_03_23_*.txt"

echo "CPU temperature:"
cat /sys/devices/platform/coretemp.0/hwmon/hwmon2/temp1_input

echo "Number of chrom* processes"
ps aux | grep -i "chrom" | grep -c crawl

echo "Number of redirectors found:"
grep -c FOUND $LOG_FILES

echo "Number of issues (opened alert):"
grep -c "Issue: alert opened" $LOG_FILES

echo "Number of Tracebacks:"
grep -c Traceback $LOG_FILES

echo "Number of websites crawled:"
psql -U postgres -c 'select count(domain) from website;' selenium_crawling | grep -v '[count|ligne]'

echo "Number of websites where a banner was found:"
psql -U postgres -c 'select count(domain) from website where iab_banner = True;' selenium_crawling | grep -v '[count|ligne]'

echo "Number of websites where a __cmpLocator was found:"
psql -U postgres -c 'select count(domain) from website where iab_banner_cmplocator = True;' selenium_crawling | grep -v '[count|ligne]'

echo "Number of websites where a __tcfapi() was found:"
psql -U postgres -c 'select count(domain) from website where tcfv2 = True;' selenium_crawling | grep -v '[count|ligne]'

grep -c Trying $LOG_FILES
