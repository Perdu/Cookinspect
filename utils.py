#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from urllib.parse import urlparse
from urllib3.exceptions import MaxRetryError
import tldextract
import publicsuffix2
import csv
import subprocess
import json

CONFIG_FILE = 'cookinspect.conf'
CONFIG_FILE_PROD = 'cookinspect_prod.conf'
CONFIG_FILE_AC = 'cookinspect_ac.conf'

# consent string set by senscritique.com p, 2019.07.25
CONSENT_STRING_SENSCRITIQUE = 'BOkQjswOkQjswBcAcBFRCc-AAAApMhv4XjiARsho1NRBJgABALiAiAAAQAAYABIFAAASgABBCAkAgAAAA4gAAEAAAABIBIAAAAAAAgAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'

SLEEP_TIME_BUTTON_CLICK         = 2
SLEEP_TIME_GET_LOGS             = 5
# On the worst observed case among 222 website loading __cmp after a
# 5s wait, the worst case (lemondeinformatique.fr) needed 2s to load
# it. Some (5 websites) needed 1s, all the rest no delay at all (after
# Selenium considers the page is loaded). So we might miss websites
# with a 2s delay, but we probably won't, or very few of them.
SLEEP_TIME_CMP_WAIT             = 3
SLEEP_TIME_REFRESH              = 3
SLEEP_TIME_COOKIE_WAIT          = 2

TIMEOUT                         = 10
MAX_TRIES_TIMEOUT               = 3

# states (do not edit)
BEFORE_ACTION = 1
AFTER_REFUSAL = 2
AFTER_ACCEPTANCE = 3

def get_domain(url, subdomain=False):
    if subdomain:
        return urlparse(url).netloc
    else:
        extracted = tldextract.extract(url)
        return "{}.{}".format(extracted.domain, extracted.suffix)

def url_to_domain(url, psl):
    parsed_uri = urlparse(url)
    domain = publicsuffix2.get_sld('{uri.netloc}'.format(uri=parsed_uri), psl)
    return domain

def quit_properly(browser):
    try:
        browser.close()
    except MaxRetryError as e:
        # Example: https://www.swingerdreamland.hu
        print("Error while trying to close browser (maybe it's already closed?): %s" % e)
    browser.quit()

def import_iab_cmp_list(short_names=False):
    CMP = {}
    if short_names:
        f = "../../datasets/cmps/IAB_CMP_list_full.csv"
    else:
        f = '../../datasets/cmps/IAB_CMP_list_full_fullnames.csv'
    reader = csv.reader(open(f, 'r'))
    first_line = True
    for row in reader:
        if first_line:
            first_line = False
            continue
        cmp_id = row[0]
        name = row[1]
        CMP[int(cmp_id)] = name
    return CMP

def decode_consent_string(consent_string):
    proc = subprocess.Popen(['node', '../decode_IAB_API_strings/decode_IAB_API_strings.js' , consent_string], stdout=subprocess.PIPE)
    (out, err) = proc.communicate()
    if proc.returncode != 0:
        print("Unable to decode consent string.")
        return None
    return json.loads(out)

def get_vendor_list(vendorlist_id=163):
    with open('../../datasets/vendor_list/vendorlist_%d.json' % int(vendorlist_id)) as json_file:
        vendorlist = json.load(json_file)
        return vendorlist
