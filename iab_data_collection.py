#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import subprocess
import json
from urllib.parse import urlparse, parse_qs
from urllib3.exceptions import ProtocolError
import publicsuffix2
import codecs
# For snippet to extract value from JSON object
from xml.dom.minidom import parseString
import xmlrpc.client
from http.client import RemoteDisconnected

from selenium.common.exceptions import *

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func

from utils import *
from identify_vendor import Webxray_database, Disconnect_database, Vendorlist_database

#re_consent_string = re.compile("consentData")
re_consent_string = re.compile('"sc-consentData=" "(.*)"')
re_consent_string2 = re.compile('"sc-metadata-vendorConsents=" "(.*)"')
re_cmp_id = re.compile('"cmpId=" "(.*)"')
# script file checking consent via postmessage caught by override-cmp
re_script_file = re.compile('sc-script-file: (.*?):\d+')
re_postmessage = re.compile('sc-postMessage: *(.*?)" ')
re_requests = re.compile('sc-requests: *(.*?)"( "POST" "(.*)")?')
re_euconsent = re.compile('"sc-cookie:" "(.*)"')
re_consent_string_postmessage = re.compile('"sc-probe-cmp-consentData:" "(.*)"')
re_consent_string_postmessage2 = re.compile('"sc-probe-cmp-vendorConsents:" "(.*)"')

def call_cmp_to_get_consent_string(browser):
    try:
        browser.execute_script('__cmp("getConsentData", null, function(val, success) { console.log("sc-consentData=",val.consentData); console.log("sc-metadata=", val.metadata)}); __cmp("getVendorConsents", null, function(val, success) { console.log("sc-consentData-vendorConsents=",val.consentData); console.log("sc-metadata-vendorConsents=", val.metadata)});', None)
    except JavascriptException as e:
        print("Exception while calling __cmp(): %s" % e)
    except TimeoutException as e:
        print("Timeout exception while calling __cmp(): %s" % e)

def get___cmp_code(browser):
    return browser.execute_script('return String(__cmp);', None)

def verify___cmp_exists(browser, website):
    # return False if publisher does not contain a __cmp() function
    try:
        # "return __cmp;" can create issues. Ex: rtl.de
        res = browser.execute_script('if (__cmp) return "ok";')
    except JavascriptException as e:
        print('__cmp not found: ', e)
        return False
    except TimeoutException:
        print("Timeout while probing for __cmp.")
        return False
    except UnexpectedAlertPresentException as e:
        # Test case: lenzeder.at
        print("Issue: alert opened when probing for __cmp. Cannot do anything. Text: %s" % e)
        website.access_successful = False
        return False
    except (RemoteDisconnected, ProtocolError):
        print("RemoteDisconnected/ProtocolError exception while probing for __cmp")
        return False
    return True

def verify___tcfapi_exists(browser, website):
    # Test if tcf v2 API exists
    # Test case : None so far
    try:
        res = browser.execute_script('if (__tcfapi) return "ok";', None)
    except JavascriptException as e:
        print('__tcfapi not found: ', e)
        return False
    except TimeoutException:
        print("Timeout while probing for __tcfapi.")
        return False
    except UnexpectedAlertPresentException as e:
        print("Issue: alert opened when probing for __tcfapi. Cannot do anything. Text: %s" % e)
        website.access_successful = False
        return False
    except (RemoteDisconnected, ProtocolError):
        print("RemoteDisconnected/ProtocolError exception while probing for __tcfapi")
        return False
    return True

def verify___cmplocator_exists(browser, website):
    # return False if publisher does not contain a __cmp() function
    try:
        # "return __cmp;" can create issues. Ex: rtl.de
        res = browser.execute_script('return document.getElementsByName("__cmpLocator").length;')
    except JavascriptException as e:
        print('__cmpLocator not found: ', e)
        return False
    except TimeoutException:
        print("Timeout while looking for __cmpLocator.")
        return False
    except UnexpectedAlertPresentException as e:
        print("Issue: alert opened when looking for __cmpLocator. Cannot do anything. Text: %s" % e)
        #website.access_successful = False
        return False
    except (RemoteDisconnected, ProtocolError):
        print("RemoteDisconnected/ProtocolError exception while looking for __cmpLocator")
        return False
    if int(res) > 0:
        return True
    return False

def get_info(entry, used_re, display_string):
    matches = used_re.search(str(entry["message"]))
    if matches is not None:
        data = matches.group(1)
        if display_string != "":
            print(display_string + ": " + data)
        return data
    return None

def get_info_multiple(entry, used_re, display_string):
    matches = used_re.search(str(entry["message"]))
    if matches is not None:
        data = matches.group(1)
        if display_string != "":
            print(display_string + ": " + data)
        res = [data]
        if matches.group(3):
            res.append(matches.group(3))
        return res
    return None

def get_consent_string(browser, website, normal=False, logs=None):
    # First arg returns consent string with a direct (first-party) call to __cmp()
    # second arg is a set of consent strings obtained through a 3rd party call
    # Test cases:
    # - Positive: senscritique.com
    # - Negative: ?
    consent_string = None
    consent_string2 = None
    consent_strings_postmessage = set()
    consent_strings_postmessage2 = set()
    if logs == None:
        # going through existing logs (call_cmp_to_get_consent_string() must be called before)
        call_cmp_to_get_consent_string(browser)
        logs = browser.get_log('browser')
    for entry in logs:
        if consent_string is None:
            consent_string = get_info(entry, re_consent_string, "Consent string")
            if consent_string == "": # prevent crash if __cmp returns a null consent string
                consent_string = None
        if consent_string2 is None:
            consent_string2 = get_info(entry, re_consent_string2, "Consent string (vendorConsents)")
            if consent_string2 == "":
                consent_string2 = None
        consent_string_postmessage = get_info(entry, re_consent_string_postmessage, "Consent string (postmessage)")
        if consent_string_postmessage == "":
            consent_string_postmessage = None
        consent_string_postmessage2 = get_info(entry, re_consent_string_postmessage2, "Consent string (postmessage, vendorConsents)")
        if consent_string_postmessage2 == "":
            consent_string_postmessage2 = None
        if consent_string_postmessage is not None:
            consent_strings_postmessage.add(consent_string_postmessage)
        if consent_string_postmessage2 is not None:
            consent_strings_postmessage2.add(consent_string_postmessage2)
    if consent_string is None:
        if normal:
            print("Consent string not found (this is normal)")
        else:
            print("Consent string not found")
    check_vendorconsents_difference(website, consent_string, consent_string2, consent_strings_postmessage, consent_strings_postmessage2)
    return consent_string, consent_strings_postmessage

def check_vendorconsents_difference(website, consent_string, consent_string2, consent_strings_postmessage, consent_strings_postmessage2):
    if consent_string2 != consent_string:
        print("**** Found 2 different consent strings. VendorConsents consent string: %s" % consent_string2)
        if consent_string is None and consent_string2 is not None:
            print("VendorConsents: only vendorConsents string is not None (site: %s)" % website.domain)
        if consent_string is not None:
            decoded_consent_string = decode_consent_string(consent_string)
            nb_purposes = len(decoded_consent_string["allowedPurposeIds"])
        else:
            nb_purposes = 0
        if consent_string2 is not None:
            decoded_consent_string2 = decode_consent_string(consent_string2)
            nb_purposes2 = len(decoded_consent_string2["allowedPurposeIds"])
            print(decoded_consent_string2)
        else:
            nb_purposes2 = 0
        if nb_purposes2 > nb_purposes:
            print("VendorConsents: more purposes set on vendorConsents string (site: %s)" % website.domain)
        elif nb_purposes2 < nb_purposes:
            print("VendorConsents: less purposes set on vendorConsents string (site: %s)" % website.domain)
    if (len(consent_strings_postmessage) == 0 and len(consent_strings_postmessage2) != 0) or (len(consent_strings_postmessage) != 0 and len(consent_strings_postmessage2) == 0):
        print("VendorConsents: consent string found in only one postmessage case (site: %s)" % website.domain)
    else:
        worst_case_postmessage = 0
        worst_case_postmessage2 = 0
        for consent_string in consent_strings_postmessage:
            decoded_consent_string = decode_consent_string(consent_string)
            nb_purposes = len(decoded_consent_string["allowedPurposeIds"])
            if nb_purposes > worst_case_postmessage:
                worst_case_postmessage = nb_purposes
        for consent_string in consent_strings_postmessage2:
            decoded_consent_string = decode_consent_string(consent_string)
            nb_purposes = len(decoded_consent_string["allowedPurposeIds"])
            if nb_purposes > worst_case_postmessage2:
                worst_case_postmessage2 = nb_purposes
        if worst_case_postmessage2 > worst_case_postmessage:
            print("VendorConsents: more purposes set on vendorConsents string in postmessage (site: %s)" % website.domain)
        elif worst_case_postmessage2 < worst_case_postmessage:
            print("VendorConsents: less purposes set on vendorConsents string in postmessage (site: %s)" % website.domain)

def find_vendor_by_id(vendorlist, vendor):
    for registered_vendor in vendorlist["vendors"]:
        if registered_vendor["id"] == vendor:
            return True
    return False

def find_vendor_by_names(vendorlist, names):
    for registered_vendor in vendorlist["vendors"]:
        for name in names:
            if name is None:
                continue
            # We check the beginning of strings and not exact matches, because IAB's vendorlist adds the company type to the name (Inc., GmBH, Ltd. etc.)
            if registered_vendor["name"].startswith(name):
                vendor_id = registered_vendor["id"]
                return vendor_id
    return None

def set_consent_set_before_violation(website, origin, phrase, consent_string, violation_level, nb_purposes):
    if violation_level > 0:
        if origin == "direct":
            if website.violation_consent_set_before_user_action_direct != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_before_user_action_direct = violation_level
        elif origin == "postmessage":
            if website.violation_consent_set_before_user_action_postmessage != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_before_user_action_postmessage = violation_level
        elif origin == "GET":
            if website.violation_consent_set_before_user_action_get != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_before_user_action_get = violation_level
        elif origin == "POST":
            if website.violation_consent_set_before_user_action_post != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_before_user_action_post = violation_level
        elif origin == "cookie":
            if website.violation_consent_set_before_user_action_cookie != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_before_user_action_cookie = violation_level
    if origin in ("direct", "postmessage", "cookie"):
        sure = False
        if nb_purposes == 0 and violation_level == 0:
            website.preaction_n0 = True
        elif nb_purposes == 0 and violation_level == 1:
            website.preaction_n1 = True
        elif nb_purposes < 5 and violation_level == 1:
            website.preaction_n2 = True
            sure = True
        elif nb_purposes == 5 and violation_level == 1:
            website.preaction_n3 = True
            sure = True
        if sure:
            website.violation_consent_set_before_user_action_sure = True
            if origin == "cookie":
                website.violation_consent_set_before_user_action_cookie_sure = True
#    else:
        # nothing to do, already handled with
        # (violation_consent_set_before_user_action_get == 1 or violation_consent_set_before_user_action_post == 1)

def set_consent_set_refusal_violation(website, origin, phrase, consent_string, violation_level, nb_purposes):
    if violation_level > 0:
        if origin == "direct":
            if website.violation_consent_set_active_refusal_direct != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_active_refusal_direct = violation_level
        elif origin == "postmessage":
            if website.violation_consent_set_active_refusal_postmessage != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_active_refusal_postmessage = violation_level
        elif origin == "GET":
            if website.violation_consent_set_active_refusal_get != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_active_refusal_get = violation_level
        elif origin == "POST":
            if website.violation_consent_set_active_refusal_post != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_active_refusal_post = violation_level
        elif origin == "cookie":
            if website.violation_consent_set_active_refusal_cookie != 1:
                print("*** VIOLATION: %s (%s).\n** Consent string: %s" % (phrase, origin, consent_string))
                website.violation_consent_set_active_refusal_cookie = violation_level
    if origin in ("direct", "postmessage", "cookie"):
        if nb_purposes == 0 and violation_level == 0:
            website.nonrespect_n0 = True
        elif nb_purposes == 0 and violation_level == 1:
            website.nonrespect_n1 = True
        elif nb_purposes < 5 and violation_level == 1:
            website.nonrespect_n2 = True
        elif nb_purposes == 5 and violation_level == 1:
            website.violation_consent_set_active_refusal_sure = True
            if origin == "cookie":
                website.violation_consent_set_active_refusal_cookie_sure = True
    else:
        if violation_level == 1 and nb_purposes == 5:
            website.violation_consent_set_active_refusal_queries_sure = True

def check_violation_consent_set(website, consent_string, origin, before_user_action=False):
    # Test cases:
    # - consent set despite active refusal: www.doctissimo.fr
    # - consent set before user action: www.tpi.it (postmessage), lepoint.fr (URL-based)
    if consent_string is not None:
        nb_vendors = len(consent_string["allowedVendorIds"])
        nb_purposes = len(consent_string["allowedPurposeIds"])
        if before_user_action:
            phrase = "Consent set in consent string before any user action"
        else:
            phrase = "Consent set in consent string despite active refusal"
        violation_level = 0
        if (nb_purposes * nb_vendors) != 0:
            violation_level = 1
        elif (nb_purposes + nb_vendors) != 0:
            # ambiguous case
            violation_level = 2
        if before_user_action:
            set_consent_set_before_violation(website, origin, phrase, consent_string, violation_level, nb_purposes)
        else:
            set_consent_set_refusal_violation(website, origin, phrase, consent_string, violation_level, nb_purposes)
        if violation_level > 0:
            if nb_vendors > 0:
                print("** Number of vendors: %s" % nb_vendors)
            if nb_purposes > 0:
                print("** Number of purposes: %s" % nb_purposes)

def check_violation_unregistered_vendors_in_consent_string(website, decoded_consent_string):
    # Test case: www.mycanal.fr (if you accept all)
    vendorlist_id = int(decoded_consent_string["vendorListVersion"])
    if vendorlist_id:
        vendorlist = get_vendor_list(vendorlist_id=vendorlist_id)
    else:
        print("Issue with the vendorlist_id: %s" % vendorlist_id)
        vendorlist = get_vendor_list()
    unregistered_vendors = []
    for vendor in decoded_consent_string["allowedVendorIds"]:
        if not find_vendor_by_id(vendorlist, vendor):
            unregistered_vendors.append(vendor)
    if unregistered_vendors != []:
        #print("*** VIOLATION: Consent set for unregistered vendors: %s" % unregistered_vendors)
        website.violation_unregistered_vendors_in_consent_string = True

def get_all_names_from_domain(domain, disconnect, webxray):
    names = webxray.get_all_names_from_domain(domain)
    names.add(disconnect.get_name_from_domain(domain))
    return names

def find_vendor_in_gvl_by_domain(domain, vendorlist, disconnect, webxray, vendorlist_database):
    # To link domain to company name, we attempt:
    # - to get the name from the webxray list (big work on link between domain
    #   and company names, including sub-companies)
    # - to get the name from the disconnect list (knows more trackers, but no
    #   work is done to know all company names)
    # - to match domain with the privacy policy URL in the vendorlist
    names = get_all_names_from_domain(domain, disconnect, webxray)
    vendor_id = find_vendor_by_names(vendorlist, names)
    if vendor_id is None:
        # attempt to link domain with privacy policy URL in vendorlist
        vendor_id = vendorlist_database.get_id_from_domain(domain)
    return vendor_id

def check_violation_vendors_2_4_5(website, domains_checking_consent):
    # Tests cases:
    # - Positive (case 2) : doctissimo.fr (doubleclick.net, get)
    # - Negative (Case 2) : lemonde.fr
    # - Positive (case 4) : doctissimo.fr (googletagmanager.com, direct)
    # - Negative (Case 4) : lemonde.fr
    # - Positive (case 5) : doctissimo.fr (3)
    # - Negative (case 5) : lemonde.fr
    violation = False
    vendorlist = get_vendor_list()
    disconnect = Disconnect_database()
    webxray = Webxray_database()
    vendorlist_database = Vendorlist_database(vendorlist)
    vendors_violation_2 = {"direct": set(), "postmessage": set(), "get": set(), "post": set()}
    vendors_violation_4 = {"direct": set(), "postmessage": set(), "get": set(), "post": set()}
    regular_checks = {"direct": set(), "postmessage": set(), "get": set(), "post": set()}
    for origin in domains_checking_consent:
        # Sometimes, postmessages come from a first party script.
        # This is worth keeping though.
        #if domain == website.domain:
        #    continue
        for domain in domains_checking_consent[origin]:
            if domain == "":
                # It's possible that we fail to identify the domain (for
                # example, when an anonymous function queries __cmp() directly).
                # Let's quantify this case.
                # Test case: https://www.freebox.fr
                print("Unknown domain checking consent.")
                website.unknown_consent_checks += 1
                continue
            is_tracker = disconnect.is_tracker(domain)
            add_domain_to_db(website, domain, is_tracker)
            vendor_id = find_vendor_in_gvl_by_domain(domain, vendorlist, disconnect, webxray, vendorlist_database)
            if vendor_id is not None: # in GVL (case 5)
                regular_checks[origin].add(domain)
            else: # not in GVL
                if is_tracker: # in Disconnect (case 2)
                    print("*** VIOLATION: Tracker (according to Disconnect) checking consent but not in Global Vendor List. Domain: %s. (case 2) (%s)" % (domain, origin))
                    vendors_violation_2[origin].add(domain)
                else: # not in Disconnect (case 4)
                    #print("*** VIOLATION: Third party (%s) checking consent but not in Disconnect's tracker list (violation by an unknown tracker? Script hosted by the company? CDN?) (case 4) (%s)" % (domain, origin))
                    vendors_violation_4[origin].add(domain)
    # Fill database according to cases
    # Violation 2
    for origin in vendors_violation_2:
        if len(vendors_violation_2[origin]) > 0:
            if origin == "direct":
                website.violation_vendor_2_direct = set(website.violation_vendor_2_direct).union(vendors_violation_2[origin])
            elif origin == "postmessage":
                website.violation_vendor_2_postmessage = set(website.violation_vendor_2_postmessage).union(vendors_violation_2[origin])
            elif origin == "get":
                website.violation_vendor_2_get = set(website.violation_vendor_2_get).union(vendors_violation_2[origin])
            elif origin == "post":
                website.violation_vendor_2_post = set(website.violation_vendor_2_post).union(vendors_violation_2[origin])
    # Violation 4
    for origin in vendors_violation_4:
        if len(vendors_violation_4[origin]) > 0:
            if origin == "direct":
                website.violation_vendor_4_direct = set(website.violation_vendor_4_direct).union(vendors_violation_4[origin])
            elif origin == "postmessage":
                website.violation_vendor_4_postmessage = set(website.violation_vendor_4_postmessage).union(vendors_violation_4[origin])
            elif origin == "get":
                website.violation_vendor_4_get = set(website.violation_vendor_4_get).union(vendors_violation_4[origin])
            elif origin == "post":
                website.violation_vendor_4_post = set(website.violation_vendor_4_post).union(vendors_violation_4[origin])
    # Regular checks (case 5)
    for origin in regular_checks:
        if len(regular_checks[origin]) > 0:
            if origin == "direct":
                website.regular_consent_verification_direct = set(website.regular_consent_verification_direct).union(regular_checks[origin])
            elif origin == "postmessage":
                website.regular_consent_verification_postmessage = set(website.regular_consent_verification_postmessage).union(regular_checks[origin])
            elif origin == "get":
                website.regular_consent_verification_get = set(website.regular_consent_verification_get).union(regular_checks[origin])
            elif origin == "post":
                website.regular_consent_verification_post = set(website.regular_consent_verification_post).union(regular_checks[origin])

def add_domain_to_db(website, domain, is_tracker):
    if is_tracker:
        # sqlalchemy returns field as a list
        website.trackers = set(website.trackers).union(set([domain]))
        if website.current_state == BEFORE_ACTION:
            website.trackers_before_action = set(website.trackers_before_action).union(set([domain]))
        elif website.current_state == AFTER_REFUSAL:
            website.trackers_after_refusal = set(website.trackers_after_refusal).union(set([domain]))
        elif website.current_state == AFTER_ACCEPTANCE:
            website.trackers_after_acceptance = set(website.trackers_after_acceptance).union(set([domain]))
    else:
        if domain != website.domain:
            website.non_trackers = set(website.non_trackers).union(set([domain]))
            if website.current_state == BEFORE_ACTION:
                website.non_trackers_before_action = set(website.non_trackers_before_action).union(set([domain]))
            elif website.current_state == AFTER_REFUSAL:
                website.non_trackers_after_refusal = set(website.non_trackers_after_refusal).union(set([domain]))
            elif website.current_state == AFTER_ACCEPTANCE:
                website.non_trackers_after_acceptance = set(website.non_trackers_after_acceptance).union(set([domain]))

def add_trackers(website, domains):
    vendorlist = get_vendor_list()
    disconnect = Disconnect_database()
    webxray = Webxray_database()
    vendorlist_database = Vendorlist_database(vendorlist)
    for domain in domains:
        vendor_id = find_vendor_in_gvl_by_domain(domain, vendorlist, disconnect, webxray, vendorlist_database)
        is_tracker = disconnect.is_tracker(domain)
        add_domain_to_db(website, domain, is_tracker)

def check_violation_vendors_1_3(website, domains_checking_consent, all_domains):
    # These "violations" were dropped from the paper
    # Test cases:
    # - Positive (case 1) : senscritique.com (17)
    # - Negative (case 1) : lepoint.fr
    # - Positive (case 3) : senscritique.com (13)
    # - Negative (case 1) : does that even exist? (todo)
    domains_not_checking_consent = all_domains - domains_checking_consent
    if website.domain in domains_not_checking_consent:
        domains_not_checking_consent.remove(website.domain)
    vendorlist = get_vendor_list()
    disconnect = Disconnect_database()
    webxray = Webxray_database()
    vendorlist_database = Vendorlist_database(vendorlist)
    violation_vendor_1 = set()
    violation_vendor_3 = set()
    for domain in domains_not_checking_consent:
        vendor_id = find_vendor_in_gvl_by_domain(domain, vendorlist, disconnect, webxray, vendorlist_database)
        is_tracker = disconnect.is_tracker(domain)
        add_domain_to_db(website, domain, is_tracker)
        if vendor_id is not None: # In GVL (case 1)
            #print("*** VIOLATION: Third party present on the website and in the Global Vendor List, but does not verify consent. Domain: %s. (case 1)" % domain)
            violation_vendor_1.add(domain)
        else:
            if is_tracker:
                #print("*** VIOLATION: Tracker present on the website is not in the Global Vendor List and does not verify consent. Domain: %s. (case 3)" % domain)
                violation_vendor_3.add(domain)
    website.violation_vendor_1 = set(website.violation_vendor_1).union(violation_vendor_1)
    website.violation_vendor_3 = set(website.violation_vendor_3).union(violation_vendor_3)

#def check_violation_vendor_not_in_consent_string(browser, website, vendors, consent_string):
    # This is actually not a violation (it's moved to "present")
    # Test case: www.republicain-lorrain.fr
#    violation = False
#    for vendor_id in vendors:
#        if vendor_id not in consent_string["allowedVendorIds"]:
#            print("*** VIOLATION: Vendor (checking consent) not in consent string: %s" % vendor_id)
#            violation = True
#    website.violation_vendor_not_in_consent_string = violation

def check_violation_shared_consent(browser, website, args):
    # Test case :
    # - Positive : altervista.org
    # - negative : lemonde.fr
    time.sleep(SLEEP_TIME_CMP_WAIT)
    consent_string, consent_strings_postmessage = get_consent_string(browser, website, normal=True)
    violation = False
    if consent_string == CONSENT_STRING_SENSCRITIQUE:
        violation = True
    for consent_string in consent_strings_postmessage:
        if consent_string == CONSENT_STRING_SENSCRITIQUE:
            violation = True
    if violation:
        website.violation_shared_cookie = True
        print("Shared consent string obtained")

def consent_string_violations(website, raw_consent_string, origin, before_user_action, tracking_accepted=False):
    if raw_consent_string is None:
        return
    if raw_consent_string in website.seen_consent_strings[origin]:
        return
    print("Found new consent string (origin: %s): %s" % (origin, raw_consent_string))
    consent_string = decode_consent_string(raw_consent_string)
    if consent_string is None:
        return
    website.seen_consent_strings[origin].add(raw_consent_string)
    if not tracking_accepted and (before_user_action or (website.violation_no_option == False and website.violation_no_banner == False)):
        # if user can't refuse consent, the "non-respect of decision" violation has no meaning
        check_violation_consent_set(website, consent_string, origin=origin, before_user_action=before_user_action)
    check_violation_unregistered_vendors_in_consent_string(website, consent_string)
    # We don't look for CMP ID in GET and POST queries because these strings are not reliable
    if origin == "GET" or origin == "POST":
        return
    cmp_id = int(consent_string["cmpId"])
    if website.cmpid is None:
        print("Found CMP ID: %d" % cmp_id)
        website.cmpid = cmp_id
    else:
        if website.cmpid != cmp_id:
            website.different_cmpids = True
            if not is_cmpid_correct_print_cmpname(website.cmpid, new=False) and is_cmpid_correct_print_cmpname(cmp_id):
                # Stored cmpid was wrong, and we found the right one
                website.cmpid = cmp_id
    if not is_cmpid_correct_print_cmpname(cmp_id):
        website.violation_incorrect_cmpid = True

def is_cmpid_correct_print_cmpname(cmp_id, new=True):
    # returns False if CMP id is incorrect
    # "new" parameter indicates wether to print result
    # Test case:
    # - positive: senscritique.com
    # - negative: heavy.com
    CMP = import_iab_cmp_list()
    if new:
        print("CMP id: %s" % cmp_id)
    if cmp_id in CMP:
        if new:
            print("CMP name: %s" % CMP[cmp_id])
        return True
    else:
        if new:
            print("Incorrect CMP id set in consent string: %d" % cmp_id)
        return False

def get_decoded_consent_string(browser, website, normal=False):
    # This function is just for iab_data_collection (might be removed)
    consent_string, consent_strings_postmessage = get_consent_string(browser, website, normal)
    if consent_string is None:
        return None
    else:
        return decode_consent_string(consent_string)

def automatic_violations_check_no_extension(browser, website, args):
    # check automatic violations
    consent_string, consent_strings_postmessage = get_consent_string(browser, website, normal=True)
    consent_string_violations(website, consent_string, origin="direct", before_user_action=True)
    for consent_string in consent_strings_postmessage:
        consent_string_violations(website, consent_string, origin="postmessage", before_user_action=True)

def get_shared_cookie(browser, website, logs=None):
    if logs is None:
        logs = browser.get_log('browser')
    for entry in logs:
        cookie = get_info(entry, re_euconsent, "")
        if cookie is not None and len(cookie) > 0:
            print("Shared cookie found!")
            return cookie
    print("Shared cookie not found.")
    return None

def headful_violations_check(browser, website, args, refusal):
    # Test case for "no option" violation:
    # - Positive : senscritique.com
    # - negative : (just use senscritique.com and validate consent)
    text = input("OK > ")
    if text.startswith("n"):
        print("ok! violation (no option)")
        website.violation_no_option = True
    elif text.startswith("p"):
        print("ok! violation (pre-ticked box)")
        website.violation_preticked = True
    elif text.startswith("b"):
        print("ok! violation (no banner)")
        website.violation_no_banner = True
    elif text.startswith("x"):
        print("ok! violation (broken banner)")
        website.violation_broken_banner = True
    time.sleep(SLEEP_TIME_COOKIE_WAIT)
    shared_cookie = get_shared_cookie(browser, website)
    tracking_accepted = not refusal and not website.violation_no_option and not website.violation_no_banner and not website.violation_broken_banner
    if shared_cookie is not None:
        website.shared_cookie_set = True
        if tracking_accepted:
            website.shared_cookie_set_acceptance = True
        else:
            website.shared_cookie_set_refusal = True
        consent_string_violations(website, shared_cookie, origin="cookie", before_user_action=False, tracking_accepted=tracking_accepted)
    raw_consent_string, consent_strings_postmessage = get_consent_string(browser, website)
    if raw_consent_string is not None:
        consent_string_violations(website, raw_consent_string, origin="direct", before_user_action=False, tracking_accepted=tracking_accepted)
    for raw_consent_string in consent_strings_postmessage:
        consent_string_violations(website, raw_consent_string, origin="postmessage", before_user_action=False, tracking_accepted=tracking_accepted)

def post_reload_violations_check(browser, website):
    seen_consent_strings = {"direct": set(), "postmessage": set(), "GET": set(), "POST": set(), "cookie": set()}
    (all_domains, domains_other) = get_through_logs_for_violations(browser, website, seen_consent_strings, try_getting_consent_string=True)
    add_trackers(website, all_domains)
    for origin in seen_consent_strings:
        for consent_string in seen_consent_strings[origin]:
            if consent_string is not None:
                consent_string_violations(website, consent_string, origin=origin, before_user_action=False)

def vendors_violations_check(browser, website, args):
    time.sleep(SLEEP_TIME_GET_LOGS)
    psl = publicsuffix2.fetch()
    domains = {"direct": set()}
    for entry in browser.get_log('browser'):
        script_file_checking_consent = get_info(entry, re_script_file, "Vendor script file")
        if script_file_checking_consent is not None:
            domain = url_to_domain(script_file_checking_consent, psl)
            domains["direct"].add(domain)
    check_violation_vendors_2_4_5(website, domains)
    return domains

def extract_from_json(json_object, string):
    # Snippet from https://stackoverflow.com/a/14050180/2678806 (fixed)
    # Test case (annoying embedded case) : 4dex prebid request on lepoint.fr
    def val(node):
        # Searches for the next Element Node containing Value
        e = node.nextSibling
        while e and e.nodeType != e.ELEMENT_NODE:
            e = e.nextSibling
        return (e.getElementsByTagName('string')[0].firstChild.nodeValue if (e and e.getElementsByTagName('string') != [] and e.getElementsByTagName('string')[0].firstChild is not None) else None)
    try:
        dom = parseString(xmlrpc.client.dumps((json_object,), allow_none=True))
    except OverflowError as e:
        print("Error decoding JSON data: %s" % e)
        return None
    try:
        res = [val(node) for node in dom.getElementsByTagName('name') if node.firstChild.nodeValue in string]
    except AttributeError as e:
        print("Error decoding JSON data: %s" % e)
        return None
    if len(res) > 0:
        return res[0]
    else:
        return None

def vendors_passive_violations_check(browser, website, domains_direct):
    seen_consent_strings = {"direct": set(), "postmessage": set(), "GET": set(), "POST": set(), "cookie": set()}
    (all_domains, domains_other) = get_through_logs_for_violations(browser, website, seen_consent_strings)
    # Now that we gathered all domains checking for consent, we can merge them
    # and verify related violations
    domains_checking_consent = domains_direct["direct"]
    for origin in domains_other:
        domains_checking_consent |= domains_other[origin]
    check_violation_vendors_1_3(website, domains_checking_consent, all_domains)
    for origin in seen_consent_strings:
        for consent_string in seen_consent_strings[origin]:
            consent_string_violations(website, consent_string, origin=origin, before_user_action=True)

def get_through_logs_for_violations(browser, website, seen_consent_strings, try_getting_consent_string=False):
    # Test case (postmessages) : www.cotemaison.fr (lots of postmessages)
    # Test case (URL-based, GET) : lepoint.fr
    # Test case (URL-based, POST) : lepoint.fr
    # Test case (Ignored GDPR, GET) : lepoint.fr
    # Test case (Ignored GDPR, POST) : lepoint.fr
    time.sleep(SLEEP_TIME_GET_LOGS)
    psl = publicsuffix2.fetch()
    domains = {"postmessage": set(), "get": set(), "post": set()}
    all_domains = set()
    if try_getting_consent_string:
        call_cmp_to_get_consent_string(browser)
    # Some doc: https://github.com/SeleniumHQ/selenium/wiki/Logging
    logs = browser.get_log('browser')
    cookie = get_shared_cookie(browser, website, logs=logs)
    if cookie is not None:
        seen_consent_strings["cookie"].add(cookie)
        website.shared_cookie_set = True
    if try_getting_consent_string:
        consent_string, consent_strings_postmessage = get_consent_string(browser, website, normal=False, logs=logs)
        seen_consent_strings["direct"].add(consent_string)
        for consent_string in consent_strings_postmessage:
            seen_consent_strings["postmessage"].add(consent_string)
    for entry in logs:
        # checking postmessages
        postmessage_origin = get_info(entry, re_postmessage, "")
        if postmessage_origin is not None:
            domain = url_to_domain(postmessage_origin, psl)
            domains["postmessage"].add(domain)
            continue
        # checking requests
        request = get_info_multiple(entry, re_requests, "")
        if request is not None:
            #print(html.unescape(request)) # should not be necessary
            parsed = urlparse(request[0])
            domain = url_to_domain(request[0], psl)
            all_domains.add(domain)
            # GET parameters
            parameters = parse_qs(parsed.query)
            if "gdpr_consent" in parameters or "gdpr" in parameters:
                domains["get"].add(domain) # add domain to vendors list
                if "gdpr_consent" in parameters and len(parameters["gdpr_consent"]) > 0:
                    #consent_string_violations(website, parameters["gdpr_consent"][0], origin="GET")
                    seen_consent_strings["GET"].add(parameters["gdpr_consent"][0])
                if "gdpr" in parameters and len(parameters["gdpr"]) > 0 and parameters["gdpr"][0] == '0':
                        if not website.violation_gdpr_does_not_apply_this_session:
                            #print("*** A request (GET) pretends GDPR does not apply")
                            website.violation_gdpr_does_not_apply_this_session = True
                        website.violation_gdpr_does_not_apply = True
            if "redirect" in parameters and "consensu.org" in domain and len(parameters["redirect"]) > 0 and str(parameters["redirect"][0]).startswith("http"):
                print("Found a consensu.org redirector respecting the specification. Request: %s" % request[0])
                website.redirector_seen = True
                # Examples: sports.fr, lematin.ch (sddan)
            elif "consensu.org" in domain and "redirect" not in parameters:
                print("Found a request to consensu.org not respecting the redirector specification. Request: %s" % request[0])
                website.other_consensu_seen = True
            # POST parameters
            if len(request) > 1:
                raw_post_data = request[1]
                post_data = None
                raw_consent_string = None
                gdpr_param = None
                try:
                    post_data = json.loads(codecs.getdecoder('unicode_escape')(raw_post_data)[0])
                    if post_data is not None:
                        raw_consent_string = extract_from_json(post_data, "gdpr_consent")
                        # extract_from_json does not work for integers. We do not look for embedded parameters.
                except json.decoder.JSONDecodeError as e:
                    if raw_post_data is list:
                        # parameters are not necessarily in JSON format
                        if "gdpr_consent" in raw_post_data:
                            print(raw_post_data)
                            raw_consent_string = raw_post_data["gdpr_consent"]
                        if "gdpr" in raw_post_data:
                            gdpr_param = raw_post_data["gdpr"]
                if raw_consent_string is not None:
                    domains["post"].add(domain) # add domain to vendors list
                    seen_consent_strings["POST"].add(raw_consent_string)
                if gdpr_param == '0' or gdpr_param == False:
                    if not website.violation_gdpr_does_not_apply_this_session:
                        #print("*** A request (POST) pretends GDPR does not apply")
                        website.violation_gdpr_does_not_apply_this_session = True
                    website.violation_gdpr_does_not_apply = True
    check_violation_vendors_2_4_5(website, domains)
    return all_domains, domains
