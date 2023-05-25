#!/bin/sh

BLUE='\033[0;34m'
NC='\033[0m'

# make sure that if a sub-command exits, this script exits too
set -e

export VERBOSE=YES

echo "${BLUE}Crawling new seattle city calendar items...${NC}\n\n"

python manage.py legistar crawl-calendar --start today

echo "\n\n${BLUE}Performing low-level document summaries...${NC}\n\n"

python manage.py documents summarize all

echo "\n\n${BLUE}Summarizing all legislative actions...${NC}\n\n"

python manage.py legistar summarize all-legislation

echo "\n\n${BLUE}Summarizing all meetings...${NC}\n\n"

python manage.py legistar summarize all-meetings

echo "\n\n${BLUE}ALL DONE UPDATING!${NC}\n\n"
