#!/bin/bash

# Give a command line argument to select the remote server, e.g. remote
if [ $# -eq 0 ]
then
    # For the Django managed sqlite database
    echo "Using local sqlite DB server..."
    rm db.sqlite3
    rm */migrations/0*.py
    gsed -i '0,/which_database/{/.*which_database.*/s//which_database="local"/}' mysite/settings.py
else
    # For the remote Mysql database server
    echo "Using remote MYSQL DB server..."
    echo "Dropping all tables"
    bash drop_all_tables.sh    
    gsed -i '0,/which_database/{/.*which_database.*/s//which_database="remote"/}' mysite/settings.py
fi

echo "Cleanup lens mugshots and temporary uploads"
rm -r media
mkdir media
mkdir media/lenses
mkdir media/temporary

echo "Makemigrations"
python manage.py makemigrations

echo "Migrate"
python manage.py migrate
