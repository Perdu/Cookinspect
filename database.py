#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import configparser
import re

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, ARRAY
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.types import LargeBinary

from utils import *

########### GLOBAL VARs
Base = declarative_base()

def start_db(prod=False, ac=False):
    if prod:
        config = parse_config_file(CONFIG_FILE_PROD)
    elif ac:
        config = parse_config_file(CONFIG_FILE_AC)
    else:
        config = parse_config_file(CONFIG_FILE)
    eng = create_engine('postgresql://' + config.db_user + ':' +
                        config.db_pass + '@' + config.db_server +
                        '/' + config.db_name, pool_recycle=3600)
    Base.metadata.bind = eng
    Session = sessionmaker(bind=eng)
    db = Session()
    Base.metadata.create_all(bind=eng)
    return db

########### CLASSES
class Config():
    def __init__(self, c):
        self.db_name = c.get('Database', 'db_name')
        self.db_server = c.get('Database', 'db_server')
        self.db_user = c.get('Database', 'db_user')
        self.db_pass = c.get('Database', 'db_pass')

class Website(Base):
    __tablename__ = "website"
    id = Column(Integer, primary_key=True)
    domain = Column(String(2083), unique=True) # https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
    main_page_url = Column(String(2083))
    last_visited = Column(DateTime)
    access_successful = Column(Boolean)
    robot_txt_ban = Column(Boolean)
    iab_banner = Column(Boolean)
    iab_banner_cmplocator = Column(Boolean)
    tcfv2 = Column(Boolean)
    iab_banner_tcfapilocator = Column(Boolean)
    cmpid = Column(Integer)
    cmp_code = Column(TEXT)
    tcfapi_code = Column(TEXT)
    # for all consent_set violations:
    # - 1 = undoubtful violation
    # - 2 = doubtful violation (no purpose is set but vendors are)
    violation_consent_set_before_user_action_direct = Column(Integer)
    violation_consent_set_before_user_action_postmessage = Column(Integer)
    violation_consent_set_before_user_action_get = Column(Integer)
    violation_consent_set_before_user_action_post = Column(Integer)
    violation_consent_set_before_user_action_cookie = Column(Integer)
    violation_consent_set_before_user_action_sure = Column(Boolean) # preaction_n2 or preaction_n3
    violation_consent_set_before_user_action_cookie_sure = Column(Boolean)
    violation_no_banner = Column(Boolean)
    violation_broken_banner = Column(Boolean)
    violation_no_option = Column(Boolean)
    violation_preticked = Column(Boolean)
    violation_consent_set_active_refusal_direct = Column(Integer)
    violation_consent_set_active_refusal_postmessage = Column(Integer)
    violation_consent_set_active_refusal_get = Column(Integer)
    violation_consent_set_active_refusal_post = Column(Integer)
    violation_consent_set_active_refusal_cookie = Column(Integer)
    violation_consent_set_active_refusal_sure = Column(Boolean) # nonrespect_n3
    violation_consent_set_active_refusal_cookie_sure = Column(Boolean)
    violation_consent_set_active_refusal_queries_sure = Column(Boolean)
    nonrespect_n0 = Column(Boolean)
    nonrespect_n1 = Column(Boolean)
    nonrespect_n2 = Column(Boolean)
    preaction_n0 = Column(Boolean)
    preaction_n1 = Column(Boolean)
    preaction_n2 = Column(Boolean)
    preaction_n3 = Column(Boolean)
    violation_shared_cookie = Column(Boolean)
    violation_unregistered_vendors_in_consent_string = Column(Boolean)
    violation_incorrect_cmpid = Column(Boolean)
    violation_vendor_1 = Column(ARRAY(String(256)))
    violation_vendor_1_legint = Column(ARRAY(String(256)))
    violation_vendor_2_direct = Column(ARRAY(String(256)))
    violation_vendor_2_postmessage = Column(ARRAY(String(256)))
    violation_vendor_2_get = Column(ARRAY(String(256)))
    violation_vendor_2_post = Column(ARRAY(String(256)))
    violation_vendor_3 = Column(ARRAY(String(256)))
    violation_vendor_4_direct = Column(ARRAY(String(256)))
    violation_vendor_4_postmessage = Column(ARRAY(String(256)))
    violation_vendor_4_get = Column(ARRAY(String(256)))
    violation_vendor_4_post = Column(ARRAY(String(256)))
    regular_consent_verification_direct = Column(ARRAY(String(256)))
    regular_consent_verification_postmessage = Column(ARRAY(String(256)))
    regular_consent_verification_get = Column(ARRAY(String(256)))
    regular_consent_verification_post = Column(ARRAY(String(256)))
    violation_gdpr_does_not_apply = Column(Boolean)
    #violation_vendor_not_in_consent_string = Column(Boolean)
    different_consent_strings = Column(Boolean)
    different_cmpids = Column(Boolean)
    shared_cookie_set = Column(Boolean)
    shared_cookie_set_refusal = Column(Boolean)
    shared_cookie_set_acceptance = Column(Boolean)
    trackers = Column(ARRAY(String(256)))
    non_trackers = Column(ARRAY(String(256)))
    trackers_before_action = Column(ARRAY(String(256)))
    trackers_after_refusal = Column(ARRAY(String(256)))
    trackers_after_acceptance = Column(ARRAY(String(256)))
    non_trackers_before_action = Column(ARRAY(String(256)))
    non_trackers_after_refusal = Column(ARRAY(String(256)))
    non_trackers_after_acceptance = Column(ARRAY(String(256)))
    consent_strings = Column(ARRAY(String(256))) # should be ok with current number of vendors, but no max length is specified
    consent_strings_v2 = Column(ARRAY(TEXT))
    nothing_found_after_manual_validation = Column(Boolean) # in case semi-automatic check finds nothing
    # sorted by origin, not stored in db (unlike above field)
    seen_consent_strings = {"direct": set(), "postmessage": set(), "GET": set(), "POST": set(), "cookie": set()}
    seen_consent_strings_v2 = {"direct": set(), "postmessage": set(), "GET": set(), "POST": set(), "cookie": set()}
    pickled_consent_strings = Column(LargeBinary)
    pickled_consent_strings_v2 = Column(LargeBinary)
    violation_gdpr_does_not_apply_this_session = False # for printing
    http_only = Column(Boolean)
    unknown_consent_checks = Column(Integer)
    semi_automatic_done = Column(Boolean)
    redirector_seen = Column(Boolean)
    other_consensu_seen = Column(Boolean)
    current_state = 0

    def __init__(self, domain):
        self.domain = domain
        self.last_visited = datetime.datetime.now()
        self.violation_vendor_1 = set()
        self.violation_vendor_2_direct = set()
        self.violation_vendor_2_postmessage = set()
        self.violation_vendor_2_get = set()
        self.violation_vendor_2_post = set()
        self.violation_vendor_3 = set()
        self.violation_vendor_4_direct = set()
        self.violation_vendor_4_postmessage = set()
        self.violation_vendor_4_get = set()
        self.violation_vendor_4_post = set()
        self.regular_consent_verification_direct = set()
        self.regular_consent_verification_postmessage = set()
        self.regular_consent_verification_get = set()
        self.regular_consent_verification_post = set()
        self.trackers = set()
        self.non_trackers = set()
        self.trackers_before_action = set()
        self.trackers_after_refusal = set()
        self.trackers_after_acceptance = set()
        self.non_trackers_before_action = set()
        self.non_trackers_after_refusal = set()
        self.non_trackers_after_acceptance = set()
        self.consent_strings = set()
        self.consent_strings_v2 = set()
        self.unknown_consent_checks = 0
        self.main_page_url = ""
        self.violation_no_option = False
        self.violation_no_banner = False

    def move_to_http(self):
        if self.main_page_url.startswith('http://'):
            return False
        self.http_only = True
        self.main_page_url = re.sub('https://', 'http://', self.main_page_url)
        print("HTTPS access failed, moving to HTTP.")
        return True

    def remove_www(self):
        if '://www.' not in self.main_page_url:
            return False
        self.main_page_url = re.sub('://www.', '://', self.main_page_url)
        print("Accessing www.domain failed, attempting domain (without www.)")
        return True

########### FUNCTIONS
def parse_config_file(config_file):
    c = configparser.RawConfigParser()
    if not c.read(config_file):
        print("Could not find config file %s." % config_file)
        print('Please copy it from %s.example and fill it appropiately.' % CONFIG_FILE)
        sys.exit(1)
    config = Config(c)
    return config
