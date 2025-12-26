#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Run migrations for Django's internal models
python manage.py migrate --no-input

# Collect static files
python manage.py collectstatic --no-input --clear
