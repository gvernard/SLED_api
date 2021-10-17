#!/bin/bash

# For the Django managed sqlite database
#rm db.sqlite3
#rm */migrations/0*.py

# For the remote Mysql database server
bash drop_all_tables.sh

python manage.py makemigrations
python manage.py migrate
python tests/database_control_scripts/populate_db.py
