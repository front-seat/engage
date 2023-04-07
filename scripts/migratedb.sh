#!/bin/sh

BLUE='\033[0;34m'
NC='\033[0m'

# reset the local development database
python manage.py migrate
