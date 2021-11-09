#!/bin/bash

# Give a command line argument to select the remote server, e.g. remote
if [ $# -eq 0 ]
then
    # For the Django managed sqlite database
    echo "Using local sqlite DB server..."
    rm db.sqlite3
    rm */migrations/0*.py
    sed -i '0,/which_database/{/.*which_database.*/s//which_database="local"/}' mysite/settings.py
else
    # For the remote Mysql database server
    echo "Using remote MYSQL DB server..."
    echo "Dropping all tables"
    bash drop_all_tables.sh    
    sed -i '0,/which_database/{/.*which_database.*/s//which_database="remote"/}' mysite/settings.py
fi

echo "Makemigrations"
python manage.py makemigrations

echo "Migrate"
python manage.py migrate
python tests/database_control_scripts/populate_db.py
python trial_sample/upload_lensed_quasars.py
