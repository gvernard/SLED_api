# DB_web
Web interface for the strong lens database

# Launching the test database

The current version of the database is built in python 3.7.3. It is recommended to create a new virtual environment and load the necessary packages through our compiled requirements.txt file, as so:

create a new virtual environment with conda:
conda create -n SLED python=3.7.3
set your current environment to this:
conda activate SLED
install the necessary packages in this environment:
pip install -r requirements.txt


If you are not copying the database file then you need to initialise it (read more here):

python manage.py migrate


Now you are ready to run the database and populate it:

create an admin superuser that can access the browser database interface
python manage.py createsuperuser
Username: admin
Password: ********
Email address: can leave blank
in a new terminal window, run the server:
python manage.py runserver
this will launch an interactive admin session that can be accessed through a browser:
http://127.0.0.1:8000/admin
enter the admin credentials to access the administration page
(you will notice an AnonymousUser is created automatically by the django-guardian package)


Run some test scripts!
go to the test_scripts directory, and run some files:
python populate_db.py 
python give_access.py 
python check_user_permissions.py


If you ever make changes to the underlying models or views, then you push them to the database by creating a migration file and migrating it:

python manage.py makemigrations
python manage.py migrate
