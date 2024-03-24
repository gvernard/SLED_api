# SLED web and API interface
Web and API interface for the Strong LEns Database (SLED)


# Launching the database locally for development


## Prerequisites

The only requirement is `docker compose`. You can install it in all major OS (see [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/) for mac users). We will use docker to start and stop a virtual machine that runs the Mysql and Django servers. Getting familiar with `docker` and `docker compose` is not necessary but some basic functionality (e.g. re-starting/stopping services, cleaning up containers, volumes, etc) could be helpful.

**Note**: You may need to prepend all the `docker` commands below with `sudo`. See also [here](https://docs.docker.com/engine/install/linux-postinstall/).



### Get the code and some data

1. Download the initialization data from [this link]().

2. Copy the tarball anywhere in your system, untar, and unzip:
```
tar xvf init_SLED.tar.gz
```

3. Take note of the path - we will call this path **<init_SLED>** (ending in *init_SLED/*).

4. Clone this repository anywhere in your system and note the path - we will call this path **<SLED_api>** (ending in *SLED_api/*).



### Launch a local development server

1. Locate the file *SLED_api/run_dev_server/docker_compose.yaml* and replace the **<init_SLED>** and **<SLED_api>** within it with your actual paths.

2. Inside the directory *run_dev_server/*, execute the following command (note that you may need to change the `docker` command to `sudo docker`):
```
docker compose up --build
```
This may take a while as various docker images are being built and python packages installed.
After this command is successful, you should see the following in your terminal:

![Django server launched in the terminal](/run_dev_server/django_success.png)

If you do, then you have successfully managed to run the SLED server, congratulations!

3. The only thing left to do is populating the database. Open a new terminal, navigate to *<SLED_api>/run_dev_server/* and execute the following commands after replacing **<init_SLED>** accordingly (note that you may need to change the `docker` command to `sudo docker`):
```
cat setup_db.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
cat <init_SLED>/database/strong_lenses_database.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
```
These two commands can be ran again if you need to reset the database.

4. Type [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser window and access the server.


### Development workflow

1. Any changes you make in the Django files (within your cloned SLED_api repo) will automatically restart the server. 

2. Note that you can restore the database in its original form at any time using the two commands from step 3 above.

3. Note that you can restore the files (lens mugshots, imaging data, etc) by downloading again the data from [this link]() and copying them at the same **<init_SLED>** path in your system as before. You could also restore your own previsouly made backup.

4. Once happy with your changes, submit a pull request.


### Contact

If you are seeking help, write to <sled-help@amnh.org>.


### Acknowledgements

Please cite [Vernardos et al. 2024]() if you are using SLED in your work.

