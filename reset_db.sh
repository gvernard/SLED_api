#!/bin/bash
rm db.sqlite3
rm */migrations/0*.py
python manage.py makemigrations
python manage.py migrate
python tests/database_control_scripts/populate_db.py
