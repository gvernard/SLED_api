#!/bin/bash
cd ..

# The value of 'which_database' needs to be specified in the settings.py file
# Here we grabe the first occurrence of this variable
eval `grep which_database mysite/settings.py | head -1`
echo "Working on database: "$which_database


# Give a command line argument to select the remote server, e.g. remote
if [ $which_database == "local" ]
then
    # For the Django managed sqlite database
    echo "Using local sqlite DB server..."
    rm db.sqlite3
    rm */migrations/0*.py
else
    # For the remote Mysql database server
    echo "Using remote MYSQL DB server..."
    echo "Dropping all tables"
    bash sensitive_db_scripts/drop_all_tables.sh    
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

cd initialise_database

python wait_tostart_db.py