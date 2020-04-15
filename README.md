# Cookinspect - Selenium-based crawler used to find violations for the "Do Cookie Banners Respect my Choice?" paper

## Dependencies

- postgresql
- python-tldextract
- python-selenium
- python-sqlalchemy
- python-publicsuffix2
- chromium-chromedriver (ubuntu)
- psycogs2 (ubuntu)
- consent-string (nodejs package)

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
