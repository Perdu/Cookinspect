#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import operator
from sqlalchemy import or_
import random

from database import *
from identify_vendor import *
from utils import import_iab_cmp_list, decode_consent_string

MIN_COUNT=5
TRANCO_LIST = "../../datasets/tranco_list/tranco_Alexa_Majestic_4NKX_2019_09_20.csv"
INVALID_CMP_IDS = (0, 1, 4095)

########### GLOBAL VARs
db = None
args = None
CMP = import_iab_cmp_list(short_names=True)

########## REUSED QUERIES

a_semi = " AND semi_automatic_done = True "
a_refusal = " AND violation_no_option = False AND violation_broken_banner is Null AND (violation_no_banner is Null or violation_no_banner = False) "

#query_preaction_consent_sure = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_sure = True"
query_preaction_consent_sure = "SELECT count(domain) FROM website WHERE (preaction_n2 = True OR violation_consent_set_before_user_action_sure = True)"
query_preaction_consent_ambi = """SELECT count(domain) FROM website where (violation_consent_set_before_user_action_postmessage > 0
OR violation_consent_set_before_user_action_direct > 0
OR violation_consent_set_before_user_action_get > 0
OR violation_consent_set_before_user_action_post > 0
OR violation_consent_set_before_user_action_cookie > 0)"""
query_preaction_consent_sure_semi = query_preaction_consent_sure + a_semi
query_preaction_consent_ambi_semi = query_preaction_consent_ambi + a_semi
query_nonrespect_sure = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_sure = True" + a_refusal
query_nonrespect_ambi = """SELECT count(domain) FROM website where (violation_consent_set_active_refusal_postmessage > 0
OR violation_consent_set_active_refusal_direct > 0
OR violation_consent_set_active_refusal_get > 0
OR violation_consent_set_active_refusal_post > 0
OR violation_consent_set_active_refusal_cookie > 0)""" + a_refusal

########### FUNCTIONS

def parse_command_line():
    global args
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-q', '--quiet', action='store_true', help="Don't display messages")
    parser.add_argument('-d', '--cmp-distribution', action='store_true', help="Print CMP distribution graph")
    parser.add_argument('--cmp-table-gdpr', action='store_true', help="Dump the latex results table by CMP (GDPR violations)")
    parser.add_argument('--cmp-table-tcf', action='store_true', help="Dump the latex results table by CMP (TCF violations)")
    parser.add_argument('-s', '--save', action='store_true', help="Save figures instead of displaying them")
    parser.add_argument('-c', '--cmpid', action='store', type=int, help="Only print results for CMP of id cmpid")
    parser.add_argument('-t', '--tld', action='store', help="Only print results for domains of given TLD")
    parser.add_argument('--wrong-cmpids', action='store_true', help="Print stats about incorrect CMP IDs")
    parser.add_argument('-l', '--latex', action='store_true', help="Dump result in a format usable directly in LaTeX")
    parser.add_argument('--country-stats', action='store_true', help="Dump country stats table")
    parser.add_argument('--country-preaction', action='store_true', help="Dump per-country preaction violation table")
    parser.add_argument('--avg-nb-checks', action='store_true', help="Compute average number of consent checks")
    parser.add_argument('--get-examples', action='store_true', help="Returns one of the most violating website for each CMP")
    parser.add_argument('-w', '--violating-websites', action='store', help="Returns list of websites performing a violation. Possible arguments: preaction-consent, non-respect, no-option, preticked, or 'all' for all TCF websites")
    parser.add_argument('--cmplocator-only', action='store_true', help="(Along with --violating-websites): only give websites on which there is a __cmpLocator iframe (i.e. detectable by cookie glasses) (for nonrespect and preaction)")
    parser.add_argument('-m', '--min-count', action='store', type=int, help="Minimum websites to be seen with given CMP/violation (for tables)")
    parser.add_argument('--per-violation-table', action='store', help="Dump per-violation table")
    parser.add_argument('--automatic-crawl', action='store_true', help="Use post-automatic crawl dataset")
    parser.add_argument('--top-trackers', action='store_true', help="Dump top trackers inclued on websites after a negative consent")
    parser.add_argument('-p', '--purposes-table', action='store_true', help="Dump the summary table of violations with the different number of purposes")
    args = parser.parse_args()

def get(query):
    res = db.execute(query)
    for row in res:
        return row[0]

def disp(query, mess, nb_domains=False, is_float=False):
    res = db.execute(query)
    for row in res:
        if not args.quiet:
            if nb_domains:
                print("%s: %s (%.2f %%)" % (mess, row[0], row[0]/nb_domains*100))
            elif is_float:
                if row[0] is not None:
                    print("%s: %.2f" % (mess, row[0]))
                else:
                    print("%s: 0" % mess)
            else:
                print("%s: %s" % (mess, row[0]))
        if nb_domains is not False:
            if nb_domains != 0:
                return row[0], row[0]/nb_domains*100
            else:
                return row[0], 0
        else:
            return row[0]

def tld_to_name(tld):
    match = {'uk': "United Kingdom", 'fr': "France", 'it': "Italy", 'pl': "Poland", 'es': "Spain", 'nl': "Netherlands", 'gr': "Greece", 'no': "Norway", 'ro': "Romania", 'pt': "Portugal", 'de': "Germany", 'fi': "Finland", 'bg': "Bulgaria", 'dk': "Denmark", 'be': "Belgium", 'at': "Austria", 'ch': "Switzerland", 'ie': "Ireland", 'cz': "Czech Republic", 'se': "Sweden", 'hr': "Croatia", 'sk': "Slovakia", 'lu': "Luxembourg", 'lt': "Lithuania", 'hu': "Hungary", 'ee': "Estonia", 'lv': "Latvia", 'is': "Iceland", 'si': "Slovenia", 'li': "Liechtenstein", 'cy': "Cyprus", 'mt': "Malta"}
    if tld in match:
        return match[tld]
    else:
        return None

def f(i):
    return '{:,}'.format(i).replace(',', ' ')

def country_stats(tld, preaction=False):
    if tld == "total":
        wtld = ""
        atld = ""
    else:
        wtld = " WHERE domain LIKE '%%.%s'" % tld
        atld = " AND domain LIKE '%%.%s'" % tld
    nb_domains_tld = get("SELECT count(domain) FROM website " + wtld)
    nb_ok_domains_tld = get("SELECT count(domain) FROM website where robot_txt_ban != True AND access_successful is NULL" + atld)
    nb_domains_iab_tld = get("SELECT count(domain) FROM website where iab_banner = True" + atld)
    nb_preaction_consent_sure_tld = get(query_preaction_consent_sure + atld)
    if nb_domains_iab_tld > 0:
        p_nb_preaction_consent_sure_tld = nb_preaction_consent_sure_tld / nb_domains_iab_tld * 100
    else:
        if preaction:
            return
        p_nb_preaction_consent_sure_tld = 0
    if not args.quiet:
        p_ok_domains_tld = nb_ok_domains_tld/nb_domains_tld*100
        p_domains_iab_tld = nb_domains_iab_tld/nb_ok_domains_tld*100
        if args.latex:
            if tld == "total":
                name_display = '\\setrow{\\bfseries} all'
                p_nb_domains_tld = 100
            else:
                #name = tld_to_name(tld)
                #if name is not None:
                #    name_display = "(" + name + ")"
                #else:
                name_display = ".%s" % tld
                p_nb_domains_tld = (nb_domains_tld / 1000.0 * 100)
                #            if nb_domains_iab_tld > 0:
            cells_preaction_consent = "\cellcolor{BrickRed!%d} %.1f\%% (%d/%s)" % (
                p_nb_preaction_consent_sure_tld,
                p_nb_preaction_consent_sure_tld,
                nb_preaction_consent_sure_tld,
                #f(nb_domains_iab_tld))
                nb_domains_iab_tld)
#            else:
#                cells_preaction_consent = " - "
            if preaction:
                print("%s & %s \\\\" % (name_display, cells_preaction_consent))
            else:
                #print("%s & \cellcolor{gray!%d} %s &  \cellcolor{gray!%d} %s (%.2f\%%) &  \cellcolor{gray!%d} %s (%.2f\%%) \\\\" % (name_display, p_nb_domains_tld, f(nb_domains_tld), p_ok_domains_tld, f(nb_ok_domains_tld), p_ok_domains_tld, p_domains_iab_tld, f(nb_domains_iab_tld), p_domains_iab_tld))
                print("%s & %s & %s (%.1f\%%) &  \cellcolor{gray!%d} %s (%.1f\%%) \\\\" % (name_display, f(nb_domains_tld), f(nb_ok_domains_tld), p_ok_domains_tld, p_domains_iab_tld * 3, f(nb_domains_iab_tld), p_domains_iab_tld))
                # I removed name_display and colors
        else:
            print("| %3s |       %4d |                  %4d (%6.2f %%) |                  %4d (%6.2f %%) | %4d (%6.2f %%) |" % (tld, nb_domains_tld, nb_ok_domains_tld, p_ok_domains_tld, nb_domains_iab_tld, p_domains_iab_tld, nb_preaction_consent_sure_tld, p_nb_preaction_consent_sure_tld))

def get_cmpids(used_tld=None, cmpid=None, display_incorrect=True, semi_automatic_only=True, reverse=True, min_count=0, violation=None):
    global CMP
    acond, wcond = get_conditions(used_tld, cmpid, violation=violation)
    if semi_automatic_only:
        query = "select cmpid, count(cmpid) as c from website where semi_automatic_done" + acond + " group by cmpid order by c desc;"
    else:
        query = "select cmpid, count(cmpid) as c from website" + wcond + " group by cmpid order by c desc;"
    res = db.execute(query)
    cmpids = []
    counts = []
    names = []
    counts_d = {}
    for row in res:
        cmpid = row[0]
        count = row[1]
        if count == 0 or count < min_count:
            continue
        if cmpid in CMP:
            name = CMP[cmpid]
        else:
            if not display_incorrect:
                continue
            name = "[incorrect]"
        #if not args.quiet:
        #    print("%s: %s (%s)" % (count, cmpid, name))
        cmpids.append(cmpid)
        counts.append(count)
        names.append(name)
        counts_d[name] = count
    if reverse:
        cmpids.reverse()
        counts.reverse()
        names.reverse()
    return counts, cmpids, names, counts_d

def graph_cmp_distribution(filter_small_cmps=True):
    tlds = ('fr', 'uk', 'ie', 'be', 'it', 'com')
    matplotlib.rcParams.update({'font.size': 17})
    fig = plt.figure(figsize=(11,6))
    colors = ["blue", "lightgray", "green", "red", "lightblue", "orange"]
    # National soccer teams colors: http://www.cahiersdufootball.net/infographie.php?id_infographie=3
    total_counts = {}
    per_country_counts = {}
    for tld in tlds:
        per_country_counts[tld] = {}
        counts, cmpids, names, counts_d = get_cmpids(display_incorrect=False, used_tld=tld)
        for name in counts_d:
            per_country_counts[tld][name] = counts_d[name]
            if name in total_counts:
                total_counts[name] += counts_d[name]
            else:
                total_counts[name] = counts_d[name]
    top_cmps_unfiltered = sorted(total_counts.items(), key=operator.itemgetter(1))
    if filter_small_cmps:
        top_cmps = []
        for cmp_tuple in top_cmps_unfiltered:
            if cmp_tuple[1] >= 5:
                top_cmps.append(cmp_tuple)
    else:
        top_cmps = top_cmps_unfiltered
    print(per_country_counts)
    successive_counts = {}
    names = []
    counts = []
    i = 0
    for tld in tlds:
        names.append([])
        counts.append([])
        for cmp_info in top_cmps:
            cmp_name = cmp_info[0]
            if cmp_name in successive_counts:
                if cmp_name in per_country_counts[tld]:
                    successive_counts[cmp_name] += per_country_counts[tld][cmp_name]
            else:
                if cmp_name in per_country_counts[tld]:
                    successive_counts[cmp_name] = per_country_counts[tld][cmp_name]
            names[i].append(cmp_name)
            if cmp_name in successive_counts:
                counts[i].append(successive_counts[cmp_name])
            else:
                counts[i].append(0)
        i += 1
    while i > 0:
        i -= 1
        plt.barh(names[i], counts[i], label=tlds[i], color=colors[i])
    plt.legend(loc='lower right')
    plt.tight_layout()
    if args.save:
        plt.savefig('../../paper/figures/cmps_distribution.eps')
    else:
        plt.show()

def set_matplotlib_params():
    # No Type 3 font
    matplotlib.rcParams['pdf.fonttype'] = 42
    matplotlib.rcParams['ps.fonttype'] = 42
    matplotlib.rcParams.update({'savefig.directory': '../../paper/figures/'})
    matplotlib.rcParams.update({'savefig.format': 'eps'})
    matplotlib.rcParams.update({'font.size': 13})

def get_conditions(used_tld, cmpid, others=False, unknown=False, incorrect=False, violation=None):
    if used_tld:
        ctld = " domain LIKE '%%.%s' " % used_tld
    else:
        ctld = ""
    if others:
        if incorrect:
            if cmpid != set():
                ccmp = " (cmpid in %s OR cmpid is Null) " % str(cmpid).replace('{', '(').replace('}', ')') #+ " AND cmpid not in (0, 1, 4095) "
            else:
                ccmp = " AND cmpid is Null "
        else:
            if cmpid != set():
                ccmp = " cmpid in %s " % str(cmpid).replace('{', '(').replace('}', ')') #+ " AND cmpid not in (0, 1, 4095) "
            else:
                ccmp = ""
    elif incorrect: # but not others
        ccmp = " cmpid in %s " % str(INVALID_CMP_IDS)
    elif unknown:
        ccmp = " cmpid is Null "
    elif cmpid is not None:
        ccmp = " cmpid = %d " % cmpid
    else:
        ccmp = ""
    if violation == 'no-option':
        cviol = " violation_no_option = True "
    elif violation == 'preticked':
        cviol = " violation_preticked = True "
    elif violation == 'preaction-consent':
        cviol = " (violation_consent_set_before_user_action_sure = True OR preaction_n2 = TRUE) "
    elif violation == 'non-respect':
        cviol = " violation_consent_set_active_refusal_sure = True "
    else:
        cviol = ""
    first = True
    cond = ""
    if ctld != "":
        cond = ctld
        first = False
    if ccmp != "":
        if first:
            cond = ccmp
            first = False
        else:
            cond = cond + " AND " + ccmp
    if cviol != "":
        if first:
            cond = cviol
            first = False
        else:
            cond = cond + " AND " + cviol
    if cond != "":
        wcond = " WHERE " + cond
        acond = " AND " + cond
        return acond, wcond
    else:
        return "", ""

def all_countries_stats(preaction=False):
    if not (args.quiet or args.latex):
        print("** Countries stats")
    if not (args.quiet or args.latex):
        print("| tld | Nb domains | Nb allowed and reachable domains | Nb domains with a __cmp function")
    #for tld in ('at', 'be', 'bg', 'hr', 'cy', 'cz', 'dk', 'eu', 'ee', 'fi', 'fr', 'de', 'gr', 'hu', 'is', 'ie', 'it', 'lv', 'li', 'lt', 'lu', 'mt', 'nl', 'no', 'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se', 'ch', 'uk', 'com', 'org'):
    for tld in ('uk', 'fr', 'pl', 'it', 'es', 'nl', 'gr', 'pt', 'de', 'ro', 'bg', 'fi', 'no', 'dk', 'be', 'at', 'ie', 'cz', 'ch', 'se', 'sk', 'hr', 'hu', 'lu', 'lt', 'lv', 'si', 'is', 'ee', 'li', 'cy', 'mt', 'com', 'org', 'eu'):
        if (tld == 'com' and args.latex):
            print("\\hline")
        country_stats(tld, preaction=preaction)
    print("\\hline")
    country_stats(tld="total", preaction=preaction)
    print("\\hline")

def dump_wrong_cmpids():
    cmpids = {}
    for website in db.query(Website).filter_by(violation_incorrect_cmpid=True):
        for raw_consent_string in website.consent_strings:
            decoded_consent_string = decode_consent_string(raw_consent_string)
            cmpid = decoded_consent_string["cmpId"]
            if cmpid not in CMP:
                print(cmpid)
                if cmpid not in cmpids:
                    cmpids[cmpid] = 1
                else:
                    cmpids[cmpid] += 1
            continue # get only one per website
    print(cmpids)

def get_ranking(domain):
    # get ranking in tranco list
    trimmed_domain = domain.replace('www.', '')
    reader = csv.reader(open(TRANCO_LIST, 'r'))
    for row in reader:
        if row[1] == trimmed_domain:
            return row[0]

def dump_stats(used_tld=None, cmpid=None, others=False, unknown=False, all_caption=False, incorrect=False):
    acond, wcond = get_conditions(used_tld, cmpid, others, unknown, incorrect)
    a_semi = " AND semi_automatic_done = True "
    nobanneroptcond = " and violation_no_option = False and (violation_no_banner = False or violation_no_banner is Null) and violation_broken_banner is Null "
    if not args.quiet:
        print("** General stats")
    nb_domains = disp('SELECT count(domain) FROM website' + wcond, "Number of domains")
    nb_domains_sa = disp('SELECT count(domain) FROM website where semi_automatic_done = True' + acond, "Number of domains on which the semi-automatic test was done")
    if incorrect and not others and nb_domains_sa < MIN_COUNT:
        return nb_domains_sa
    nb_domains_sa_refusal, a  = disp('SELECT count(domain) FROM website where semi_automatic_done = True' + a_refusal + acond, "Number of domains on which the semi-automatic test was done and refusing consent was possible", nb_domains_sa)
    nb_ok_domains, percentage = disp('SELECT count(domain) FROM website where robot_txt_ban != True AND access_successful is NULL' + acond, 'Number of allowed and reachable domains', nb_domains)
    nb_domains_iab, percentage = disp('SELECT count(domain) FROM website where iab_banner = True' + acond, "Number of domains with an IAB banner", nb_ok_domains)
    if not args.quiet:
        disp('SELECT count(domain) FROM website where robot_txt_ban = True' + acond, 'Number of unauthorized domains', nb_domains)
        disp('SELECT count(domain) FROM website WHERE access_successful = False' + acond, "Number of failed accesses", nb_domains)
        disp('SELECT count(domain) FROM website where iab_banner_cmplocator = True' + acond, "Number of domains with a cmplocator", nb_domains_iab)
        disp('SELECT count(domain) FROM website WHERE robot_txt_ban = True' + acond, "Number of refused accesses", nb_domains)
        nb_ok_https_domains = get("select count(main_page_url) from website where main_page_url LIKE 'https://%' and access_successful is null" + acond)
        nb_ok_http_domains = get("select count(main_page_url) from website where main_page_url LIKE 'http://%' and access_successful is null" + acond)
        print("Websites reachable through HTTP only: %s (%.2f %%)" % (nb_ok_http_domains, nb_ok_http_domains / (nb_ok_http_domains + nb_ok_https_domains) * 100))
        # nb_domains_cmplocator, percentage = disp('SELECT count(domain) FROM website where iab_banner_cmplocator = True' + acond, "(Fix) Number of domains with no __cmp function but a __cmpLocator", nb_ok_domains)
        disp('SELECT count(domain) FROM website where tcfv2 = True' + acond, "Number of domains implementing TCF v2", nb_ok_domains)
        disp('SELECT count(domain) FROM website WHERE cmpid is not NULL' + acond, "Number of cmpid found", nb_domains_iab)
        disp('SELECT count(domain) FROM website WHERE cmpid is not NULL and semi_automatic_done = True' + acond, "Number of cmpid found (semi-automatic crawl)", nb_domains_sa)
        disp('SELECT count(domain) FROM website WHERE cmpid is not NULL AND cmpid not in (0,1,4095)' + acond, "Number of correct cmpid found", nb_domains_iab)
        disp('SELECT count(domain) FROM website WHERE cmpid is not NULL and semi_automatic_done = True AND cmpid not in (0,1,4095)' + acond, "Number of correct cmpid found (semi-automatic crawl)", nb_domains_sa)
        disp("SELECT count(main_page_url) from website where main_page_url LIKE 'http://%' and access_successful is null and iab_banner = True" + acond, "Number of website using the TCF and reachable through HTTP only", nb_domains_iab)

    if not args.quiet:
        print("\n** Violations")
    v_preaction_consent_sure, p_v_preaction_consent_sure = disp(query_preaction_consent_sure + acond, "Violation: pre-action consent (= non respect of choice) (sure only)", nb_domains_iab)
    if not args.quiet:
        disp("SELECT count(domain) FROM website WHERE preaction_n0 = True AND preaction_n1 is Null AND preaction_n2 is Null AND preaction_n3 is Null" + acond, "preaction n0 (no purpose, no vendor)", nb_domains_iab)
        disp("SELECT count(domain) FROM website WHERE preaction_n1 = True AND preaction_n2 is Null AND preaction_n3 is Null" + acond, "preaction n1 (no purpose, vendors)", nb_domains_iab)
        disp("SELECT count(domain) FROM website WHERE preaction_n2 = True OR preaction_n3 = True" + acond, "preaction n2 or n3 (1-5 purposes)", nb_domains_iab)
        disp("SELECT count(domain) FROM website WHERE preaction_n1 = True OR preaction_n2 = True OR preaction_n3 = True" + acond, "preaction n1 or n2 or n3 (0-5 purposes)", nb_domains_iab)
        disp(query_preaction_consent_ambi + acond, "preaction n1-3 + all queries", nb_domains_iab)
    v_0_purposes_preaction, p_v_0_purposes_preaction = disp("SELECT count(domain) FROM website WHERE (preaction_n0 = True OR preaction_n1 = True) AND preaction_n2 is Null AND preaction_n3 is Null" + acond, "preaction n0+n1 (no purpose)", nb_domains_iab)
    v_1_4_purposes_preaction, p_v_1_4_purposes_preaction = disp("SELECT count(domain) FROM website WHERE preaction_n2 = True AND preaction_n3 is Null" + acond, "preaction n2 (1-4 purposes)", nb_domains_iab)
    v_5_purposes_preaction, p_v_5_purposes_preaction = disp("SELECT count(domain) FROM website WHERE preaction_n3 = True" + acond, "preaction n3 (5 purposes)", nb_domains_iab)
    v_preaction_consent_sure_semi, p_v_preaction_consent_sure_semi = disp(query_preaction_consent_sure_semi + acond, "Violation: pre-action consent (semi-automatic crawl) (sure only)", nb_domains_sa)
    v_no_banner, p_v_no_banner = disp('SELECT count(domain) FROM website WHERE violation_no_banner = True' + acond, "Violation: no banner", nb_domains_sa)
    v_broken_banner, p_v_broken_banner = disp('SELECT count(domain) FROM website WHERE violation_broken_banner = True' + acond, "Violation: broken banner", nb_domains_sa)
    v_nooption, p_v_nooption = disp('SELECT count(domain) FROM website WHERE violation_no_option = True' + acond, "Violation: no option", nb_domains_sa)
    if not args.quiet:
        disp('SELECT count(domain) FROM website WHERE (violation_no_option = True OR violation_no_banner = True OR violation_broken_banner = True)' + acond, "Violation: no banner, option, or purpose option, or broken banner ", nb_domains_sa)
    v_preticked, p_v_preticked = disp('SELECT count(domain) FROM website WHERE violation_preticked = True' + acond, "Violation: pre-ticked", nb_domains_sa_refusal)
    v_nonrespect_sure, p_v_nonrespect_sure = disp(query_nonrespect_sure + acond, "Violation: non-respect of decision (sure only)", nb_domains_sa_refusal)
    if not args.quiet:
        #disp("SELECT count(domain) FROM website WHERE nonrespect_n0 = True" + acond + a_refusal, "nonrespect n0 (no purpose, no vendor)", nb_domains_sa_refusal)
        disp("SELECT count(domain) FROM website WHERE nonrespect_n0 = True AND nonrespect_n1 is Null AND nonrespect_n2 is Null and violation_consent_set_active_refusal_sure is Null" + acond + a_refusal, "nonrespect n0 (no purpose, no vendor)", nb_domains_sa_refusal)
        disp("SELECT count(domain) FROM website WHERE nonrespect_n1 = True AND nonrespect_n2 is Null AND violation_consent_set_active_refusal_sure is Null" + acond + a_refusal, "nonrespect n1 (no purpose, vendors)", nb_domains_sa_refusal)
        disp("SELECT count(domain) FROM website WHERE nonrespect_n2 = True OR violation_consent_set_active_refusal_sure = True" + acond + a_refusal, "nonrespect n2 or n3 (1-5 purposes)", nb_domains_sa_refusal)
        disp("SELECT count(domain) FROM website WHERE nonrespect_n1 = True OR nonrespect_n2 = True OR violation_consent_set_active_refusal_sure = True" + acond + a_refusal, "nonrespect n1 or n2 or n3 (0-5 purposes)", nb_domains_sa_refusal)
        disp(query_nonrespect_ambi + acond, "nonrespect n1-3 + all queries", nb_domains_sa_refusal)
    v_0_purposes_nonrespect, p_v_0_purposes_nonrespect = disp("SELECT count(domain) FROM website WHERE (nonrespect_n0 = True OR nonrespect_n1 = True) AND nonrespect_n2 is Null AND violation_consent_set_active_refusal_sure is Null" + acond + a_refusal, "nonrespect n0 or n1 (no purpose)", nb_domains_sa_refusal)
    v_1_4_purposes_nonrespect, p_v_1_4_purposes_nonrespect = disp("SELECT count(domain) FROM website WHERE nonrespect_n2 = True AND violation_consent_set_active_refusal_sure is Null" + acond + a_refusal, "nonrespect n2 (1-4 purposes)", nb_domains_sa_refusal)
    v_shared, p_v_shared = disp('SELECT count(domain) FROM website WHERE violation_shared_cookie = True' + acond, "Using (reading) shared cookie", nb_domains_iab)
    if not args.quiet:
        disp('SELECT count(domain) FROM website where violation_consent_set_before_user_action_cookie = 1' + acond, "Violation (huge): Nb websites setting the shared cookie before user action (1-5 purposes)", nb_domains_iab)
        #disp('SELECT count(domain) FROM website where violation_consent_set_active_refusal_cookie > 0' + acond, "Violation (huge): Nb websites setting the shared cookie despite user refusal (sure and ambiguous)", nb_domains_sa_refusal)
        disp('SELECT count(domain) FROM website where violation_consent_set_active_refusal_cookie = 1' + acond, "Violation (huge): Nb websites setting the shared cookie despite user refusal (1-5 purposes)", nb_domains_sa_refusal)
        disp('SELECT count(domain) FROM website where violation_consent_set_active_refusal_cookie_sure = True' + acond, "Violation (huge): Nb websites setting the shared cookie despite user refusal (5 purposes)", nb_domains_sa_refusal)
        disp("""SELECT count(domain) FROM website where semi_automatic_done AND
        (violation_consent_set_before_user_action_postmessage > 0
        OR violation_consent_set_before_user_action_direct > 0
        OR violation_consent_set_before_user_action_get > 0
        OR violation_consent_set_before_user_action_post > 0
        OR violation_consent_set_before_user_action_cookie > 0
        OR violation_consent_set_active_refusal_postmessage > 0
        OR violation_consent_set_active_refusal_direct > 0
        OR violation_consent_set_active_refusal_get > 0
        OR violation_consent_set_active_refusal_post > 0
        OR violation_consent_set_active_refusal_cookie > 0)""" + acond, "Violation: violation of consent (pre-action or despite refusal) (sure or ambiguous)", nb_domains_sa_refusal)
        disp("""SELECT count(domain) FROM website where semi_automatic_done AND
        (violation_consent_set_before_user_action_sure = True OR preaction_n2 = TRUE
        OR violation_consent_set_active_refusal_sure = True
        )""" + acond, "Violation: violation of consent (pre-action or despite refusal) (sure only)", nb_domains_sa_refusal)
        disp("""SELECT count(domain) FROM website where semi_automatic_done AND
        (violation_consent_set_before_user_action_sure = True OR preaction_n2 = TRUE
        OR violation_consent_set_active_refusal_sure = True
        OR violation_no_option
        OR violation_no_banner
        OR violation_broken_banner
        OR violation_preticked
        )""" + acond, "Summary (semi-automatic-crawl): any problem with consent (violation of consent (sure), no option, no banner, no purpose option, broken banner, pre-ticked option)", nb_domains_sa)
        disp("""SELECT count(domain) FROM website where iab_banner = True AND
        (violation_consent_set_before_user_action_sure = True OR preaction_n2 = TRUE
        OR violation_consent_set_active_refusal_sure = True
        OR violation_no_option
        OR violation_no_banner
        OR violation_broken_banner
        OR violation_preticked
        )""" + acond, "Summary (automatic crawl): any problem with consent (violation of consent (sure), no option, no banner, no purpose option, broken banner, pre-ticked option)", nb_domains_iab)
    if not args.quiet:
        print("\n** Weird behaviours")
        disp('SELECT count(domain) FROM website where different_consent_strings = True' + acond, "Nb websites with different consent strings caught in automatic crawl", nb_domains_iab)
        disp('SELECT count(domain) FROM website where different_cmpids = True' + acond, "Nb websites setting consent strings with different cmpids", nb_domains_iab)
        disp('SELECT count(domain) FROM website where nothing_found_after_manual_validation = True' + acond, "Nb websites on which no consent string is found even after manual validation", nb_domains_sa)
    v_unregistered_vendors, p_v_unregistered_vendors = disp('SELECT count(domain) FROM website WHERE violation_unregistered_vendors_in_consent_string = True' + acond, "Consent to non-existent vendors", nb_domains_iab)
    disp('SELECT count(domain) FROM website WHERE violation_unregistered_vendors_in_consent_string = True' + acond + a_semi, "Consent to non-existent vendors (SAC)", nb_domains_sa)
    v_wrongcmpid, p_v_wrongcmpid = disp('SELECT count(domain) FROM website WHERE violation_incorrect_cmpid = True' + acond, "Wrong CMP ID", nb_domains_iab)
    #v_vendors1, p_v_vendors1 = disp('SELECT count(domain) FROM website where array_length(violation_vendor_1, 1) > 0'+ acond, "Vendors violation 1", nb_domains_iab)
    #v_vendors1_legint, p_v_vendors1_legint = disp('SELECT count(domain) FROM website where array_length(violation_vendor_1_legint, 1) > 0'+ acond, "Vendors violation 1 (excluding legitimate interests vendors)", nb_domains_iab)
    #v_vendors1_avg = disp('select avg(array_length(violation_vendor_1, 1)) from website where array_length(violation_vendor_1, 1) > 0' + acond, "Violation: consent not verified, average number of vendors")
    #v_vendors1_avg_legint = disp('select avg(array_length(violation_vendor_1_legint, 1)) from website where array_length(violation_vendor_1_legint, 1) > 0' + acond, "Violation: consent not verified, average number of vendors (excluding legitimate interests vendors)")

    if others:
        name = "\\textbf{others}"
    elif incorrect:
        name = "\\textbf{incorrect CMP ID}"
    elif unknown:
        name = "\\textbf{No consent string found}"
    elif cmpid is not None:
        if used_tld is None:
            cmp_name = ""
            if cmpid in CMP:
                cmp_name = CMP[cmpid]
            else:
                cmp_name = "[incorrect]"
            name = cmp_name #str(cmpid) + cmp_name
        else:
            name = CMP[cmpid]
    elif all_caption:
        name = '\\setrow{\\bfseries} all'
    elif used_tld is not None:
        name = used_tld
    else:
        name = '\\setrow{\\bfseries} all'
    if args.cmp_table_gdpr:
        print("%s & %d & \cellcolor{BrickRed!%d} %.1f\%% (%d/%d) & \cellcolor{BrickRed!%d} %.1f\%% (%d/%d) & \cellcolor{BrickRed!%d} %.1f\%% (%d/%d) & \cellcolor{BrickRed!%d} %.1f\%% (%d/%d) \\\\\hline" % (name, nb_domains_sa, int(p_v_preaction_consent_sure_semi), p_v_preaction_consent_sure_semi, v_preaction_consent_sure_semi, nb_domains_sa, int(p_v_nooption), p_v_nooption, v_nooption, nb_domains_sa, int(p_v_preticked), p_v_preticked, v_preticked, nb_domains_sa_refusal, int(p_v_nonrespect_sure), p_v_nonrespect_sure, v_nonrespect_sure, nb_domains_sa_refusal))
    #elif args.cmp_table_tcf:
    #    print("%s & \cellcolor{gray!%d} %.1f\%% (%d/%d) & \cellcolor{gray!%d} %.1f\%% (%d/%d) \\\\\hline" % (name, int(p_v_vendors2), p_v_vendors2, v_vendors2, nb_domains_iab, int(p_v_vendors4), p_v_vendors4, v_vendors4, nb_domains_iab))

    if incorrect and not others:
        return nb_domains_sa
    elif args.per_violation_table:
        return name, nb_domains_sa, nb_domains_sa_refusal, v_nooption, v_preticked, v_preaction_consent_sure_semi, v_nonrespect_sure
    elif args.purposes_table:
        return nb_domains_iab, nb_domains_sa, nb_domains_sa_refusal, p_v_nooption, v_nooption, p_v_preticked, v_preticked, p_v_5_purposes_preaction, v_5_purposes_preaction, p_v_nonrespect_sure, v_nonrespect_sure, p_v_0_purposes_preaction, v_0_purposes_preaction, p_v_1_4_purposes_preaction, v_1_4_purposes_preaction, p_v_0_purposes_nonrespect, v_0_purposes_nonrespect, p_v_1_4_purposes_nonrespect, v_1_4_purposes_nonrespect

    if not args.quiet:
        print("\n** Regular behaviour")
        disp('SELECT count(domain) FROM website WHERE violation_shared_cookie = True and semi_automatic_done = True' + acond, "Using (reading) shared cookie (SA crawl)", nb_domains_sa)
        disp('SELECT count(domain) FROM website where shared_cookie_set = True' + acond, "Nb websites setting the shared cookie", nb_domains_iab)
        disp('SELECT count(domain) FROM website where shared_cookie_set = True' + acond + a_semi, "Nb websites setting the shared cookie (semi-automatic only)", nb_domains_sa)
        disp('SELECT count(domain) from website where shared_cookie_set_acceptance = True and shared_cookie_set_refusal is null' + acond, "Violation: websites setting shared cookie only upon acceptance", nb_domains_iab)

        print("\n** Trackers")
        disp('select avg(COALESCE(array_length(trackers, 1), 0)) from website where iab_banner = True' + acond + a_semi, "Average number of trackers (on SAC websites)", is_float=True)
        disp('select avg(COALESCE(array_length(trackers_before_action, 1), 0)) from website where iab_banner = True' + acond + a_semi, "Average number of trackers before action (on SAC websites)", is_float=True)
        disp('select avg(COALESCE(array_length(trackers_after_refusal, 1), 0)) from website where iab_banner = True' + nobanneroptcond + acond + a_semi, "Average number of trackers after refusal (on SAC websites)", is_float=True)
        disp('select count(*) from website where array_length(trackers_after_refusal, 1) is not NULL AND iab_banner = True' + nobanneroptcond + acond + a_semi, "Websites with trackers after refusal (SAC)", nb_domains_sa_refusal)
        disp('select avg(COALESCE(array_length(trackers_after_acceptance, 1), 0)) from website where iab_banner = True' + nobanneroptcond + acond + a_semi, "Average number of trackers after acceptance (on SAC websites)", is_float=True)
        disp('select avg(COALESCE(array_length(non_trackers, 1), 0)) from website where iab_banner = True' + acond + a_semi, "Average number of non-trackers (on SAC websites)", is_float=True)
        disp('select avg(COALESCE(array_length(non_trackers_before_action, 1), 0)) from website where iab_banner = True' + acond + a_semi, "Average number of non_trackers before action (on SAC websites)", is_float=True)
        disp('select avg(COALESCE(array_length(non_trackers_after_refusal, 1), 0)) from website where iab_banner = True' + nobanneroptcond + acond + a_semi, "Average number of non_trackers after refusal (on SAC websites)", is_float=True)
        disp('select count(*) from website where array_length(non_trackers_after_refusal, 1) is not NULL AND iab_banner = True' + nobanneroptcond + acond + a_semi, "Websites with non_trackers after refusal (SAC)", nb_domains_sa_refusal)
        disp('select avg(COALESCE(array_length(non_trackers_after_acceptance, 1), 0)) from website where iab_banner = True' + nobanneroptcond + acond + a_semi, "Average number of non_trackers after acceptance (on SAC websites)", is_float=True)
        disp('select COUNT(domain) from website where array_length(trackers, 1) is Null AND iab_banner = True' + acond, "Websites with no detected tracker (please use --automatic crawl option)", nb_domains_iab)
        disp('select COUNT(domain) from website where array_length(trackers, 1) is Null AND iab_banner = True' + acond + a_semi, "Websites with no detected tracker (SAC)", nb_domains_sa)

    if not args.quiet:
        print("\n** Origin of violations caught")
        query_preaction_consent_direct = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_direct = 1"
        query_preaction_consent_postmessage = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_postmessage = 1"
        query_preaction_consent_cookie = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_cookie = 1"
        query_preaction_consent_cookie_sure = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_cookie_sure = True"

        query_nonrespect_direct = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_direct = 1" + a_refusal
        query_nonrespect_postmessage = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_postmessage = 1" + a_refusal
        query_nonrespect_cookie = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_cookie = 1" + a_refusal
        query_nonrespect_cookie_sure = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_cookie_sure = True" + a_refusal

        query_preaction_consent_get = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_get = 1"
        query_preaction_consent_post = "SELECT count(domain) FROM website where violation_consent_set_before_user_action_post = 1"
        query_preaction_consent_queries = "SELECT count(domain) FROM website where (violation_consent_set_before_user_action_post = 1 OR violation_consent_set_before_user_action_get = 1)"
        query_preaction_consent_queries_only = "SELECT count(domain) FROM website where (preaction_n2 is Null AND violation_consent_set_before_user_action_sure is Null) AND (violation_consent_set_before_user_action_post = 1 OR violation_consent_set_before_user_action_get = 1)"
        query_nonrespect_get = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_get = 1" + a_refusal
        query_nonrespect_post = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_post = 1" + a_refusal
        query_nonrespect_queries = "SELECT count(domain) FROM website where (violation_consent_set_active_refusal_get = 1 OR violation_consent_set_active_refusal_post = 1)" + a_refusal
        query_nonrespect_queries_sure = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_queries_sure = True" + a_refusal
        query_nonrespect_queries_only = "SELECT count(domain) FROM website where violation_consent_set_active_refusal_sure is Null AND violation_consent_set_active_refusal_queries_sure = True" + a_refusal

        disp(query_preaction_consent_direct + acond, "Violation: pre-action consent (direct, semi-sure only)", nb_domains_iab)
        disp(query_preaction_consent_postmessage + acond, "Violation: pre-action consent (postmessage, semi-sure only)", nb_domains_iab)
        disp(query_preaction_consent_get + acond, "Violation: pre-action consent (get, 1-5 purposes)", nb_domains_iab)
        disp(query_preaction_consent_post + acond, "Violation: pre-action consent (post, 1-5 purposes)", nb_domains_iab)
        disp(query_preaction_consent_queries + acond, "Violation: pre-action consent (queries (GET or POST), 1-5 purposes)", nb_domains_iab)
        disp(query_preaction_consent_queries_only + acond, "Violation: pre-action consent (queries (GET or POST) only, 1-5 purposes)", nb_domains_iab)
        disp(query_preaction_consent_cookie + acond, "Violation: pre-action consent (cookie, semi-sure only)", nb_domains_iab)
        disp(query_preaction_consent_cookie_sure + acond, "Violation: pre-action consent (cookie, sure only)", nb_domains_iab)
        disp(query_nonrespect_direct + acond, "Violation: non-respect of decision (direct, semi-sure only)", nb_domains_sa_refusal)
        disp(query_nonrespect_postmessage + acond, "Violation: non-respect of decision (postmessage, semi-sure only)", nb_domains_sa_refusal)
        disp(query_nonrespect_get + acond, "Violation: non-respect of decision (get, 1-5 purposes)", nb_domains_sa_refusal)
        disp(query_nonrespect_post + acond, "Violation: non-respect of decision (post, 1-5 purposes)", nb_domains_sa_refusal)
        disp(query_nonrespect_queries + acond, "Violation: non-respect of decision (queries (get or post), 1-5 purposes)", nb_domains_sa_refusal)
        if not args.automatic_crawl:
            disp(query_nonrespect_queries_sure + acond, "Violation: non-respect of decision (queries (get or post), 5 purposes)", nb_domains_sa_refusal)
            disp(query_nonrespect_queries_only + acond, "Violation: non-respect of decision (queries (get or post) only, 5 purposes)", nb_domains_sa_refusal)
        disp(query_nonrespect_cookie + acond, "Violation: non-respect of decision (cookie, semi-sure only)", nb_domains_sa_refusal)
        disp(query_nonrespect_cookie_sure + acond, "Violation: non-respect of decision (cookie, sure only)", nb_domains_sa_refusal)

    if not args.quiet:
        print("\n** Consent redirection mechanism:")
        disp("select count(*) from website where redirector_seen = True" + acond, "Redirectors seen", nb_domains_iab)
        disp("select count(*) from website where redirector_seen = True" + a_semi + acond, "Redirectors seen (SAC)", nb_domains_sa)

    if not args.quiet:
        print("\n** Consent verification stats (not used in the paper because it's not exhaustive)")
        query_consent_verification = """SELECT count(domain) FROM website where (array_length(regular_consent_verification_direct, 1) > 0
        OR array_length(regular_consent_verification_postmessage, 1) > 0
        OR array_length(regular_consent_verification_get, 1) > 0
        OR array_length(regular_consent_verification_post, 1) > 0) AND iab_banner = True"""
        disp(query_consent_verification + acond, "Regular consent verification (this is not exhaustive)", nb_domains_iab)
        disp(query_consent_verification + acond + a_semi, "Regular consent verification (SAC only)", nb_domains_sa)
        disp(query_consent_verification + acond + " AND (semi_automatic_done is NULL OR semi_automatic_done = False) ", "Regular consent verification (AC only)", nb_domains_iab - nb_domains_sa)
        disp("SELECT count(domain) from website where array_length(regular_consent_verification_direct, 1) > 0", "Number of domains with at least one domain performing consent verification using method: direct", nb_domains_iab)
        disp("SELECT count(domain) from website where array_length(regular_consent_verification_postmessage, 1) > 0", "Number of domains with at least one domain performing consent verification using method: postmessage", nb_domains_iab)
        disp("SELECT count(domain) from website where array_length(regular_consent_verification_get, 1) > 0", "Number of domains with at least one domain performing consent verification using method: get", nb_domains_iab)
        disp("SELECT count(domain) from website where array_length(regular_consent_verification_post, 1) > 0", "Number of domains with at least one domain performing consent verification using method: post", nb_domains_iab)
        disp("""SELECT count(domain) from website where (
        array_length(regular_consent_verification_direct, 1) > 0
        OR array_length(regular_consent_verification_postmessage, 1) > 0
        OR array_length(regular_consent_verification_get, 1) > 0
        OR array_length(regular_consent_verification_post, 1) > 0
        )""", "Number of domains with at least one domain performing consent verification using method: any", nb_domains_iab)
        disp('SELECT count(domain) FROM website where unknown_consent_checks > 0' + acond, "Nb websites on which we failed to identify a domain checking for consent.", nb_domains_iab)
        v_vendors2, p_v_vendors2 = disp("""SELECT count(domain) FROM website where (array_length(violation_vendor_2_direct, 1) > 0
        OR array_length(violation_vendor_2_postmessage, 1) > 0
        OR array_length(violation_vendor_2_get, 1) > 0
        OR array_length(violation_vendor_2_post, 1) > 0)""" + acond, "Vendors violation 2: Tracker (according to Disconnect) checking consent but not in Global Vendor List", nb_domains_iab)
        #v_vendors3, p_v_vendors3 = disp('SELECT count(domain) FROM website where array_length(violation_vendor_3, 1) > 0' + acond, "Vendors violation 3", nb_domains_iab)
        v_vendors4, p_v_vendors4 = disp("""SELECT count(domain) FROM website where (array_length(violation_vendor_4_direct, 1) > 0
        OR array_length(violation_vendor_4_postmessage, 1) > 0
        OR array_length(violation_vendor_4_get, 1) > 0
        OR array_length(violation_vendor_4_post, 1) > 0)""" + acond, "Vendors violation 4: third party checking consent but not in Disconnect's tracker list", nb_domains_iab)

def get_violating_websites(violation, max_number=10):
    # preaction-consent, non-respect, no-option, preticked
    unsorted = {}
    if violation == 'all':
        for website in db.query(Website).filter_by(iab_banner=True):
            if args.cmplocator_only and website.iab_banner_cmplocator != True:
                continue
            ranking = get_ranking(website.domain)
            unsorted[ranking] = website.domain
    elif violation == 'no-option':
        for website in db.query(Website).filter_by(violation_no_option=True):
            ranking = get_ranking(website.domain)
            unsorted[ranking] = website.domain
    elif violation == 'preticked':
        for website in db.query(Website).filter_by(violation_preticked=True):
            ranking = get_ranking(website.domain)
            unsorted[ranking] = website.domain
    elif violation == 'preaction-consent':
        for website in db.query(Website).filter(or_(Website.violation_consent_set_before_user_action_sure == True, Website.preaction_n2 == True)):
            if args.cmplocator_only and website.iab_banner_cmplocator != True:
                continue
            ranking = get_ranking(website.domain)
            unsorted[ranking] = website.domain
    elif violation == 'non-respect':
        for website in db.query(Website).filter_by(violation_consent_set_active_refusal_sure=True):
            if args.cmplocator_only and website.iab_banner_cmplocator != True:
                continue
            ranking = get_ranking(website.domain)
            unsorted[ranking] = website.domain
    i = 0
    for website in sorted(unsorted, key=int):
        if args.latex:
            print("%s & %s \\\\" % (f(int(website)), unsorted[website].replace('www.', '')))
            i += 1
            if i == max_number:
                break
        else:
            print("%s,%s" % (website, unsorted[website].replace('www.', '')))
    if args.latex:
        print("\hline")

def get_example(cmpid, case, positive=True):
    if positive:
        search = "%s = True" % case
    else:
        search = "(%s = False OR %s is Null)" % (case, case)
    res = db.execute("SELECT domain from website where cmpid = %s and %s ORDER BY random() LIMIT 1" % (cmpid, search))
    for row in res:
        print("%s: %s" % (cmpid, row[0]))
        return True
    return False

def compute_avg_nb_checks():
    if args.automatic_crawl:
        cond = ""
    else:
        cond = " AND semi_automatic_done = True"
    cond_only = " AND (array_length(regular_consent_verification_direct, 1) > 0 OR array_length(regular_consent_verification_postmessage, 1) > 0 OR array_length(regular_consent_verification_get, 1) > 0 OR array_length(regular_consent_verification_post, 1) > 0)"
    query = "SELECT (regular_consent_verification_direct || regular_consent_verification_postmessage || regular_consent_verification_get || regular_consent_verification_post) FROM website WHERE iab_banner = True" + cond + cond_only
    res = db.execute(query)
    nb_checks = 0
    i = 0
    for row in res:
        nb_checks += len(set(row[0]))
        i += 1
    print(nb_checks/i)

def print_violation_table(cmpid=None, violation=None, others=False, incorrect=False, unknown=False, all_caption=False):
    violation_stats = []
    domains_stats = []
    name = ""
    nb_domains_sa = 0
    for tld in (None, 'uk', 'fr', 'it', 'be', 'ie', 'com'):
        name, nb_domains_sa, nb_domains_sa_refusal, v_nooption, v_preticked, v_preaction_consent_sure_semi, v_nonrespect_sure = dump_stats(cmpid=cmpid, used_tld=tld, others=others, incorrect=incorrect, unknown=unknown, all_caption=all_caption)
        if violation == 'no-option':
            violation_stats.append(v_nooption)
            domains_stats.append(nb_domains_sa)
        elif violation == 'preticked':
            violation_stats.append(v_preticked)
            domains_stats.append(nb_domains_sa_refusal)
        elif violation == 'preaction-consent':
            violation_stats.append(v_preaction_consent_sure_semi)
            domains_stats.append(nb_domains_sa)
        elif violation == 'non-respect':
            violation_stats.append(v_nonrespect_sure)
            domains_stats.append(nb_domains_sa_refusal)
    res = "%33s" % name
    i = 0
    for violation_stat in violation_stats:
        if domains_stats[i] > 0:
            p = violation_stat / domains_stats[i] * 100
            res += " & \cellcolor{BrickRed!%d} %.1f\%% (%d/%d)" % (int(p), p, violation_stat, domains_stats[i])
        else:
            res += " &                    - "
        i += 1
    res += "\\\\"
    print(res)

def per_violation_table(violation):
    args.quiet = True
    a, cmpids, b, c = get_cmpids(semi_automatic_only=True, reverse=False, min_count=MIN_COUNT, violation=violation)
    for cmpid in cmpids:
        if cmpid in INVALID_CMP_IDS:
            continue
        print_violation_table(cmpid, violation)
    a, cmpids_all, b, c = get_cmpids(semi_automatic_only=True, reverse=False)
    cmpids_few_res = set()
    #nb_websites = dump_stats(cmpid=None, incorrect=True)
    for cmpid in cmpids_all:
        # only add incorrect CMPids in the "others" section if not already displayed in the "incorrect" section
        #if nb_websites >= MIN_COUNT and cmpid in INVALID_CMP_IDS:
        #    continue
        if cmpid not in cmpids:
            cmpids_few_res.add(cmpid)
    if cmpids_few_res != set():
        print_violation_table(cmpid=cmpids_few_res, others=True, incorrect=True, violation=violation)
    #if violation == 'no-option' or violation == 'preticked':
    #    print_violation_table(unknown=True, violation=violation)
    print("\\hline")
    print_violation_table(cmpid=None, all_caption=True, violation=violation)
    print("\\hline")

def dump_trackers(n=20):
    disconnect = Disconnect_database()
    nb_domains_sa_refusal = get('SELECT count(domain) FROM website where semi_automatic_done = True' + a_refusal)
    query = "SELECT trackers_after_refusal FROM website;"
    res = db.execute(query)
    d = {}
    for website in res:
        trackers = website[0]
        seen_companies = set()
        for tracker in trackers:
            company = disconnect.get_name_from_domain(tracker)
            #if company is None:
            #    print("problem")
            if company not in seen_companies:
                seen_companies.add(company)
                if company in d:
                    d[company] += 1
                else:
                    d[company] = 1
    i = 0
    for e in sorted(d.items(), key=operator.itemgetter(1), reverse=True):
        p = e[1]/nb_domains_sa_refusal*100
        # manually extracted from IAB's vendor list
        if e[0] in ("AppNexus", "RubiconProject", "comScore", "Integral Ad Science", "Casale Media", "Criteo", "Adform", "Yahoo!", "The Trade Desk", "OpenX", "Quantcast", "MediaMath", "Adobe", "DataXu", "PubMatic", "Horyzon Media", "SiteScout", "SmartAdServer"):
            part_of_iab = "\ding{51}"
        else:
            part_of_iab = ""
        print("%s & \cellcolor{BrickRed!%d} %d (%.1f\%%) & %s \\\\\hline" % (e[0], int(p), e[1], p, part_of_iab))
        i += 1
        if i == n:
            break

def purposes_table():
    args.quiet = True
    nb_domains_iab, nb_domains_sa, nb_domains_sa_refusal, p_nooption, v_nooption, p_preticked, v_preticked, p_5_purposes_preaction, v_5_purposes_preaction, p_nonrespect_sure, v_nonrespect_sure, p_0_purposes_preaction, v_0_purposes_preaction, p_1_4_purposes_preaction, v_1_4_purposes_preaction, p_0_purposes_nonrespect, v_0_purposes_nonrespect, p_1_4_purposes_nonrespect, v_1_4_purposes_nonrespect = dump_stats()
    #print("0 purpose & %.2f\%% & - & - & %.2f\%% \\\\\hline" % (p_0_purposes_preaction, p_0_purposes_nonrespect))
    print("1 to 4 purposes & \\textbf{%.1f\%%} (%d/%d) & - & - & %.1f\%% (%d/%d) \\\\\hline" % (p_1_4_purposes_preaction, v_1_4_purposes_preaction, nb_domains_iab, p_1_4_purposes_nonrespect, v_1_4_purposes_nonrespect, nb_domains_sa_refusal))
    print("5 purposes & \\textbf{%.1f\%%} (%d/%d) & - & - & \\textbf{%.1f\%%} (%d/%d) \\\\\hline" % (p_5_purposes_preaction, v_5_purposes_preaction, nb_domains_iab, p_nonrespect_sure, v_nonrespect_sure, nb_domains_sa_refusal))
    print("\\textbf{Total number of violations} & %.1f\%% (%d/%d) & %.1f\%% (%d/%d) & %.1f\%% (%d/%d) & %.1f\%% (%d/%d) \\\\\hline" % (p_5_purposes_preaction + p_1_4_purposes_preaction, v_5_purposes_preaction + v_1_4_purposes_preaction, nb_domains_iab, p_nooption, v_nooption, nb_domains_sa, p_preticked, v_preticked, nb_domains_sa_refusal, p_nonrespect_sure, v_nonrespect_sure, nb_domains_sa_refusal))
    #print("\\textbf{Total} & %.2f\%% & %.2f\%% & %.2f\%% & %.2f\%%" % (p_preaction_consent_sure, p_nooption, p_preticked, p_nonrespect_sure))

if __name__ == "__main__":
    parse_command_line()
    if args.automatic_crawl:
        db = start_db(ac=True)
    else:
        db = start_db(prod=True)
    if args.cmp_distribution:
        set_matplotlib_params()
    if args.min_count:
        MIN_COUNT = args.min_count

    if args.cmp_distribution:
        graph_cmp_distribution()
    elif args.wrong_cmpids:
        dump_wrong_cmpids()
    elif args.avg_nb_checks:
        compute_avg_nb_checks()
    elif args.purposes_table:
        purposes_table()
    elif args.cmp_table_gdpr or args.cmp_table_tcf:
        if args.tld:
            tld = args.tld
        else:
            tld = None
        if args.cmp_table_gdpr:
            semi_automatic_only=True
        else:
            semi_automatic_only=False
        args.quiet = True
        a, cmpids, b, c = get_cmpids(semi_automatic_only=semi_automatic_only, reverse=False, min_count=MIN_COUNT, used_tld=tld)
        for cmpid in cmpids:
            if cmpid not in INVALID_CMP_IDS:
                dump_stats(cmpid=cmpid, used_tld=tld)
        a, cmpids_all, b, c = get_cmpids(semi_automatic_only=semi_automatic_only, reverse=False, used_tld=tld)
        cmpids_few_res = set()
        nb_websites = dump_stats(cmpid=None, incorrect=True, used_tld=tld)
        for cmpid in cmpids_all:
            # only add incorrect CMPids in the "others" section if not already displayed in the "incorrect" section
            if nb_websites >= MIN_COUNT and cmpid in INVALID_CMP_IDS:
                continue
            if cmpid not in cmpids:
                cmpids_few_res.add(cmpid)
        dump_stats(cmpid=cmpids_few_res, others=True, used_tld=tld)
        dump_stats(unknown=True, used_tld=tld)
        dump_stats(cmpid=None, used_tld=tld, all_caption=True)
    elif args.country_stats:
        all_countries_stats()
    elif args.country_preaction:
        all_countries_stats(preaction=True)
    elif args.per_violation_table:
        per_violation_table(args.per_violation_table)
        #print('&\multicolumn{6}{l}{\\bf Non-respect of decision} \\\\ \hline')
        #per_violation_table("non-respect")
        #print('&\multicolumn{6}{l}{\\bf No option} \\\\ \hline')
        #per_violation_table("no-option")
        #print('&\multicolumn{6}{l}{\\bf Pre-action consent} \\\\ \hline')
        #per_violation_table("preaction-consent")
        #print('&\multicolumn{6}{l}{\\bf Pre-ticked} \\\\ \hline')
        #per_violation_table("preticked")
    elif args.get_examples:
        #MIN_COUNT=0 # uncomment to get all CMPs
        a, cmpids, b, c = get_cmpids(semi_automatic_only=True, reverse=False, min_count=MIN_COUNT, used_tld=args.tld)
        print("Active refusal:")
        i = 0
        for cmpid in cmpids:
            found = get_example(cmpid, "violation_consent_set_active_refusal_sure")
            if found:
                i += 1
        print("\nEgal number of negative examples:")
        for cmpid in random.sample(cmpids, i):
            get_example(cmpid, "violation_consent_set_active_refusal_sure", positive=False)
        i = 0
        print("\nNo option:")
        for cmpid in cmpids:
            found = get_example(cmpid, "violation_no_option")
            if found:
                i += 1
        print("\nEgal number of negative examples:")
        for cmpid in random.sample(cmpids, i):
            get_example(cmpid, "violation_no_option", positive=False)
        #print("Preticked:")
        #for cmpid in cmpids:
        #    get_example(cmpid, "violation_preticked")
    elif args.violating_websites is not None:
        get_violating_websites(args.violating_websites)
    elif args.top_trackers:
        dump_trackers()
    else:
        dump_stats(used_tld=args.tld, cmpid=args.cmpid)
        #all_countries_stats()
