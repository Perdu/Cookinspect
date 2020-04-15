#!/bin/bash

M=3
M2=5

echo "Recomputing purposes table..."
python extract_results.py --purposes-table > ../../paper/tables/purposes.tex

echo "Recomputing country table..."
python extract_results.py --country-stats --latex > ../../paper/tables/country_table.tex
python extract_results.py --country-preaction --latex > ../../paper/tables/country_preaction.tex

echo "Recomputing CMP-GDPR table..."
python extract_results.py --cmp-table-gdpr > ../../paper/tables/cmp_table_gdpr.tex

#echo "Recomputing CMP-TCF table..."
#python extract_results.py --cmp-table-tcf > ../../paper/tables/cmp_table_tcf.tex

#echo "Recomputing CMP distribution graph..."
#rm ../../paper/figures/cmps_distribution.eps
#python extract_results.py -ds

echo "generating per country GDPR tables..."
python extract_results.py --cmp-table-gdpr -t fr -m $M2 > ../../paper/tables/cmp_table_gdpr_fr.tex
python extract_results.py --cmp-table-gdpr -t it -m $M2 > ../../paper/tables/cmp_table_gdpr_it.tex
python extract_results.py --cmp-table-gdpr -t uk -m $M2 > ../../paper/tables/cmp_table_gdpr_uk.tex
python extract_results.py --cmp-table-gdpr -t ie -m $M2 > ../../paper/tables/cmp_table_gdpr_ie.tex
python extract_results.py --cmp-table-gdpr -t be -m $M2 > ../../paper/tables/cmp_table_gdpr_be.tex
python extract_results.py --cmp-table-gdpr -t com -m $M2 > ../../paper/tables/cmp_table_gdpr_com.tex

echo "generating per violation GDPR table..."
#python extract_results.py --per-violation-table -m $M > ../../paper/tables/cmp_table_gdpr_per_country.tex
python extract_results.py --per-violation-table "non-respect" -m $M > ../../paper/tables/cmp_table_gdpr_nonrespect.tex
python extract_results.py --per-violation-table "no-option" -m $M > ../../paper/tables/cmp_table_gdpr_nooption.tex
python extract_results.py --per-violation-table "preaction-consent" -m $M > ../../paper/tables/cmp_table_gdpr_preaction.tex
python extract_results.py --per-violation-table "preticked" -m $M > ../../paper/tables/cmp_table_gdpr_preticked.tex

# Moved to the APF paper
#echo "generating vendorlist figures..."
#rm ../../paper/figures/vendorlist_evolution.eps
#python ../vendorstats/vendorlist_evolution.py --save
#rm ../../paper/figures/defined_purposes.eps
#python ../vendorstats/purpose_stats.py --defined-purposes --save
#rm ../../paper/figures/features.eps
#python ../vendorstats/purpose_stats.py --features --save

echo "Computing top trackers table..."
python extract_results.py --top-trackers > ../../paper/tables/top_trackers.tex

#exit

echo "Recomputing violating websites..."
python extract_results.py -l -w preaction-consent > ../../paper/tables/websites_violation_preaction.tex
python extract_results.py -l -w no-option > ../../paper/tables/websites_violation_nooption.tex
python extract_results.py -l -w non-respect > ../../paper/tables/websites_violation_nonrespect.tex
python extract_results.py -l -w preticked > ../../paper/tables/websites_violation_preticked.tex

echo "Recomputing attachments..."
python extract_results.py -w preaction-consent > ../../paper/attachments/websites_violation_preaction_consent.csv
python extract_results.py -w no-option > ../../paper/attachments/websites_violation_no_option.csv
python extract_results.py -w non-respect > ../../paper/attachments/websites_violation_non_respect.csv
python extract_results.py -w preticked > ../../paper/attachments/websites_violation_preticked.csv
# vendors-related attachments not included
