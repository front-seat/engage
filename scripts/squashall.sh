#!/bin/bash

# Squash and recreate all migrations.

# First, delete all files in server/documents/migrations except __init__.py
rm -f server/documents/migrations/[0-9]*.py
rm -rf server/documents/migrations/__pycache__
rm -rf server/legistar/migrations

# Now use a heredoc to recreate server/documents/migrations/0001_initial.py
cat <<EOF > server/documents/migrations/0001_initial.py
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [VectorExtension()]

EOF

# Finally, run makemigrations
python manage.py makemigrations documents --name models
python manage.py makemigrations legistar
