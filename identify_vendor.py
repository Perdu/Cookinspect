#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

from utils import *

class Webxray_database:
    def __init__(self):
        self.companies = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/webxray_resources/domain_owners_grouped.json', 'r', encoding='utf-8'))

    def get_all_names_from_domain(self, domain):
        for company in self.companies:
            if domain in company["domains"]:
                return set(company["names"])
        return set()

class Disconnect_database:
    def __init__(self):
        self.companies = {}
        self.domains = set()
        self.domain_to_name = {}
        entities = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/disconnect_resources/entities.json', 'r', encoding='utf-8'))
        for e in entities:
            self.companies[e] = set()
            for url in entities[e]["properties"]:
                self.companies[e].add(url)
                self.domains.add(url)
                self.domain_to_name[url] = e
            for url in entities[e]["resources"]:
                self.companies[e].add(url)
                self.domains.add(url)
                self.domain_to_name[url] = e

    def is_tracker(self, domain):
        return domain in self.domains

    def get_name_from_domain(self, domain):
        try:
            return self.domain_to_name[domain]
        except KeyError:
            return None

class Vendorlist_database:
    # Extract domain from privacy policy URL
    def __init__(self, vendorlist):
        psl = publicsuffix2.fetch()
        self.domain_to_id = {}
        self.id_to_vendor = {}
        for vendor in vendorlist["vendors"]:
            # get privacy policy domain
            domain = url_to_domain(vendor["policyUrl"], psl)
            self.domain_to_id[domain] = vendor["id"]
            self.id_to_vendor[vendor["id"]] = vendor

    def get_id_from_domain(self, domain):
        try:
            return self.domain_to_id[domain]
        except KeyError:
            return None

    def get_vendor(self, vendor_id):
        try:
            return self.id_to_vendor[vendor_id]
        except KeyError:
            return None
