#!/bin/bash

set -eu -o pipefail

BLUE="\e[34m"
NC="\e[0m"

# Run Python formatter -- but let Django migrations get a pass.
printf "${BLUE}Running ruff format...${NC}\n"
ruff format --check server

# Run Python linter (ruff).
printf "${BLUE}Running ruff...${NC}\n"
ruff check server

# Run the Python type checker (pyright).
# (Oddly, the python type checker itself is written in... typescript!)
printf "${BLUE}Running pyright...${NC}\n"
npx pyright

# Run Python tests
printf "${BLUE}Running backend tests...${NC}\n"
python manage.py test

# See if we can generate the static site
printf "${BLUE}Generating static site...${NC}\n"
python manage.py distill-local --force --collectstatic > /dev/null
printf "${BLUE}...(successfully generated)${NC}\n"


