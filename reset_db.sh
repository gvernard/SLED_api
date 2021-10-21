#!/bin/bash

# For the Django managed sqlite database
#rm db.sqlite3
#rm */migrations/0*.py

# For the remote Mysql database server
echo "Dropping all tables"
bash drop_all_tables.sh

echo "Makemigrations"
python manage.py makemigrations

echo "Migrate"
python manage.py migrate
python tests/database_control_scripts/populate_db.py
