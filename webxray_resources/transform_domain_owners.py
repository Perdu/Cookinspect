#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Transforms the domain owners file into a json file containing groups
# containing all domains and names of each company.

# Author: Célestin Matte, 2019

import json
import os

def create_groups(domain_owner_data):
    dicts = []
    while domain_owner_data != []:
        company = domain_owner_data[0]
        if company["parent_id"] is None:
            s = {}
            s[company["id"]] = company
            dicts.append(s)
            domain_owner_data = domain_owner_data[1:]
        else:
            found = False
            for s in dicts:
                if company["parent_id"] in s:
                    s[company["id"]] = company
                    domain_owner_data = domain_owner_data[1:]
                    found = True
                    break
            if found == False:
                domain_owner_data = domain_owner_data[1:] + [domain_owner_data[0]]
    return dicts

def display_groups(dicts):
    res = []
    for d in dicts:
        domains = []
        names = []
        for index in d:
            company = d[index]
            for domain in company["domains"]:
                domains.append(domain)
            names.append(company["owner_name"])
            for alias in company["aliases"]:
                names.append(alias)
        res.append({"domains": domains, "names": names})
    print(json.dumps(res))

if __name__ == "__main__":
    domain_owner_data = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/webxray_resources/domain_owners.json', 'r', encoding='utf-8'))
    dicts = create_groups(domain_owner_data)
    display_groups(dicts)
