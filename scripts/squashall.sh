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

# Run new migrate
python manage.py migrate

# Create a superuser. You must have your environment variables set.
# Check that DJANGO_SUPERUSER_EMAIL is set.
if [ -z "$DJANGO_SUPERUSER_EMAIL" ]; then
  echo "DJANGO_SUPERUSER_EMAIL is not set. Will not create a superuser."
  exit 0
fi

python manage.py createsuperuser --noinput
