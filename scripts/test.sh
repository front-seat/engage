#!/bin/bash

set -eu -o pipefail

BLUE="\e[34m"
NC="\e[0m"

# Run Python formatter -- but let Django migrations get a pass.
printf "${BLUE}Running ruff format...${NC}\n"
ruff format --check server
ruff format --check crawl

# Run Python linter (ruff).
printf "${BLUE}Running ruff...${NC}\n"
ruff check server
ruff check crawl

# Run the Python type checker (pyright).
# (Oddly, the python type checker itself is written in... typescript!)
printf "${BLUE}Running pyright...${NC}\n"
npx pyright

# Run Python tests
printf "${BLUE}Running backend tests...${NC}\n"
python manage.py test

