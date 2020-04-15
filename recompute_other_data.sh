#!/bin/bash

echo "Recomputing offending violating .fr websites..."
python extract_results.py -w preaction-consent | grep -F '.fr' > ../../datasets/offending_websites/preaction-consent_fr.csv
python extract_results.py -w non-respect | grep -F '.fr' > ../../datasets/offending_websites/non-respect_fr.csv
python extract_results.py -w preticked | grep -F '.fr' > ../../datasets/offending_websites/preticked_fr.csv
python extract_results.py -w no-option | grep -F '.fr' > ../../datasets/offending_websites/no-option_fr.csv

echo "Recomputing offending violating websites..."
python extract_results.py -w preaction-consent > ../../datasets/offending_websites/preaction-consent.csv
python extract_results.py -w non-respect > ../../datasets/offending_websites/non-respect.csv
python extract_results.py -w preticked > ../../datasets/offending_websites/preticked.csv
python extract_results.py -w no-option > ../../datasets/offending_websites/no-option.csv
