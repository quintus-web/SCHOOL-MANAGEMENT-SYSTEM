#!/usr/bin/env bash
set -o errexit

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --verbosity 0 --skip-checks

echo "=== Running database migrations ==="
python manage.py migrate --noinput --skip-checks

echo "=== Seeding student data ==="
python manage.py seed_data --skip-checks

echo "=== Build complete ==="
