#!/bin/bash

# Squash and recreate all migrations.

# Delete our database
rm -f data/db.sqlite3

# Delete all migrations
rm -rf server/documents/migrations
rm -rf server/legistar/migrations

# Run new makemigrations
python manage.py makemigrations documents --name models
python manage.py makemigrations legistar
