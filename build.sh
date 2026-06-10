#!/usr/bin/env bash
set -o errexit

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --verbosity 0

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Seeding student data ==="
python manage.py seed_data

echo "=== Build complete ==="
