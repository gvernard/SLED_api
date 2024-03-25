# SLED web and API interface
Web and API interface for the Strong LEns Database (SLED)


# Launching the database locally for development


## Prerequisites

The only requirement is `docker compose`. You can install it in all major OS (see [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/) for mac users). We will use docker to start and stop a virtual machine that runs the Mysql and Django servers. Getting familiar with `docker` and `docker compose` is not necessary but some basic functionality (e.g. re-starting/stopping services, cleaning up containers, volumes, etc) could be helpful.

**Note**: You may need to prepend all the `docker` commands below with `sudo`. See also [here](https://docs.docker.com/engine/install/linux-postinstall/).



## Get the code and some data

1. Download the initialization data from [this link]().

2. Copy the tarball anywhere in your system, untar, and unzip:
```
tar xvf init_SLED.tar.gz
```

3. Take note of the path - we will call this path **<init_SLED>** (ending in *init_SLED/*).

4. Clone this repository anywhere in your system and note the path - we will call this path **<SLED_api>** (ending in *SLED_api/*).



## Launch a local development server

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



## Development workflow

1. Any changes you make in the Django files (within your cloned SLED_api repo) will automatically restart the server. 

2. If you edit or add any new model, then django will need to edit or create a new database table accordingly. The best approach is to simply quit and restart the docker containers (with the `docker compose` command above).

3. Once happy with your changes, submit a pull request. Note that this should include only software changes and all data injected in the database should be excluded. If the request is approved then the data can be re-injected in the production server. Developers should keep this in mind and plan accordingly.



## Advanced commands

It is important to know how to clean up the docker containers and all associated data. The following commands destroy the docker containers and associated volume and can allow for a fresh start:
```
docker compose down
docker volume rm run_dev_server_data
```

Cleaning up all the django migrations may be required if having problems while editing the existing django models or adding new ones. It can be achieved via (in the *SLED_api/* directory):
```
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 
find . -path "*/migrations/*.pyc"  -delete
```

If you need to inspect the running docker containers you can attach a shell to them via:
```
docker exec -it SLED_server bash
docker exec -it SLED_database bash
```

If you need to access the database (e.g. run a custom MySQL query directly) then execute:
```
docker exec -it SLED_database bash -c 'mysql -h localhost -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
```




## Contact

Write to <sled-help@amnh.org> if everything else fails.


## Acknowledgements

Please cite [Vernardos et al. 2024]() if you are using SLED in your work.

