#!/bin/bash

# For the Django managed sqlite database
#rm db.sqlite3
#rm */migrations/0*.py

# For the remote Mysql database server
#mysql -h 127.0.0.1 -P 8888 -u sled_root -p -D strong_lenses_database -e "drop database strong_lenses_database; create database strong_lenses_database;"
bash ../drop_all_tables.sh

python manage.py makemigrations
python manage.py migrate
python tests/database_control_scripts/populate_db.py
