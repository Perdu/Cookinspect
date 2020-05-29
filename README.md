# Cookinspect

Selenium-based crawler used to find violations in cookie banners of IAB Europe's Transparency &amp; Consent Framework

## Introduction

In the paper [Do Cookie Banners Respect my Choice? Measuring Legal Compliance of Banners from IAB Europe's Transparency and Consent Framework](https://arxiv.org/abs/1911.09964), we show that Consent Management Providers (CMPs) of IAB Europe's Transparency & Consent Framework (TCF) do not always respect user's choice. This repository contains the code of the crawler used for this paper.

Author: Célestin Matte (Université Côte d'Azur, Inria, France)

## Dependencies

- postgresql
- python-tldextract
- python-selenium
- python-sqlalchemy
- python-publicsuffix2
- chromium-chromedriver (ubuntu)
- psycogs2 (ubuntu)
- consent-string (nodejs package)
- wget (to download vendorlists)

## Install procedure

### Database
- Create a postgresql database called "cookinspect", along with a "cookinspect" user and give appropriate access rights.

```bash
$ psql -c 'create database cookinspect'
$ psql cookinspect
# create role cookinspect;
# alter role cookinspect with login;
# grant connect on database cookinspect to cookinspect;
# grant all on database cookinspect to cookinspect;
```

### Configuration
- copy cookinspect.conf.example to cookinspect.conf and modify it according to your database configuration.

### Vendor lists
In order to detect violations, you need to download all vendor lists from IAB. Fortunately, there is a script that does that automatically.

```bash
cd vendorlist
./download.sh
```

IAB produces a new vendor list every week, so you need to launch this script again if you reuse cookinspect and it crashes because the latest vendorlist is not found.

### Consent string decoding
(Unnecessary if you don't decode consent strings, e.g. if you only want to detect the presence of banners)
Install IAB's consent string nodejs package:

``npm install --save consent-string``

### Potential installs issue
- You may need to add a password to your database user so that sqlalchemy lets you connect

## Usage

``python cookinspect.py [--full-violations-check|--automatic-violations-check|--semi-automatic-violations-check|--help]``

Run it with --help for more options.
By default, the script will attempt to load the website and say if it contains a TCF-related CMP.

### Displaying results

To display results for a single website, use the --dump option.

To display statistics on all websites present in the database, use

``python extract_results.py``

### Running a campaign on many websites
- Copy the list of websites in a CSV file, without www. subdomain (this will be tested automatically). See an example in examples/iab_banners.csv
- Use run.sh:

	``run.sh DOMAINS_LIST_FILE OUTPUT_LOG_FILE [--semi-automatic|--full|--test-cmp]``

It runs the automatic crawl by default.

### Security caution
This tool takes a lot of inputs from the targeted website and has not been built with security in mind. Someone reading this code COULD exploit it. Please do not run outside a safe environment, e.g. at least a separate unix user having no right on your system.
