# DB_web
Web interface for the strong lens database

# Launching the test database

The current version of SLED is built in python 3.7.3. It is recommended to create a new virtual environment and load the necessary packages through our compiled requirements.txt file, as so:

create a new virtual environment with conda:
```sh
conda create -n SLED python=3.7.3
```

and set your current environment to this:
```sh
conda activate SLED
```

To install the necessary packages in this environment, first run
```sh
conda install mysqlclient=2.0.3
```
and then
```sh
pip install -r misc/requirements.txt
```

As the actual database we are using a remote Mysql (MariaDB) server.
This has been set up in the 'settings.py' file and requires a 'my.cnf' file with the credentials, which, obviously, is not and must not be publicly accessible.
Before running the server or any tests, one needs to run:

ssh -f <username>@login01.astro.unige.ch -L 8888:mysql10.astro.unige.ch:4006 -N

where <username> is your username for the Geneva observatory.
This is because the Mysql server runs in the internal network and the only way to access it from the outside is through an SSH tunnel.
This is what the above command sets up in the background, it maps 'localhost' and a port, through the gateway server (login01) to the Mysql configured machine.
The SSH tunnel might be closed if the connection gets interrupted - just run it again.


The database is initialized (or reset) by running:

bash reset_db.sh

which requires two Mysql scripts, 'drop_all_tables.sh' and 'function_distance_on_sky.sql'.
The first one resets all the tables in the database, erasing all inserted data, and the second one defines a custom user function (stored function) that the database server will perform.
It calculates the distance between two points on a sphere in arsec and is required to check proximity of lenses.
These two scripts contain passwords and must NOT be publicly accessible.

**It is advised to create a directory outside the git-tracked one to keep the my.cnf, drop_all_tables.sh, and function_distance_on_sky.sh scripts.
Then use symbolic links to link these scripts where they are expected: the first in mysite/ and the other two at the project root dir.**


Now you are ready to run the server (in a new terminal window):

python manage.py runserver

This will launch an interactive admin session that can be accessed through a browser:
http://127.0.0.1:8000/admin

enter the admin credentials to access the administration page

(you will notice an AnonymousUser is created automatically by the django-guardian package)


You can also choose to run some test scripts.
Go to the test_scripts directory, and run some files:

python testing_user_functions.py
python confirmation_task.py
python testing_lenses.py


If you ever make changes to the underlying models or views, then you push them to the database by creating a migration file and migrating it:

python manage.py makemigrations
python manage.py migrate

If you want to include a dummy email server, then use: python -m smtpd -n -c DebuggingServer localhost:1025


**For Mac users, you need to install gnu-sed and then either alias sed to point to it or use gsed in reset.sh**
