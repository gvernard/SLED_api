# SLED web and API interface
Web and API interface for the Strong LEns Database (SLED)


# Launching the database locally for development


## Prerequisites

The only requirement is `docker compose`. You can install it in all major OS. We will use docker virtualization to start and stop a virtual machine that runs the Mysql and Django servers. Getting familiar with `docker` and `docker compose` is not necessary but some basic functionality (e.g. re-starting/stopping services) could be helpful.


### Get the code and some data

1. Download the initialization data from [this link]().

2. Copy the tarball anywhere in your system and note the path - we will call this path <init_SLED> from now on.

3. Untar and unzip
```
tar xvf init_SLED.tar.gz
```

4. Clone this repository anywhere in your system and note the path - we will call this path <SLED_api> from now on.


### Launch a development server locally

1. Locate the file docker_compose.yaml in the directory run_dev_server and replace the <init_SLED> and <SLED_api> with your actual paths.

2. In the same directory, run the following command:
```
docker compose up --build
```
This may take a while as various VMs and packages are being fetched.
If this command is successful, congratulations, you have an instance of SLED running!

3. The last thing left is to populate the database. Open a new terminal in the same directory and run
```
cat setup_db.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
cat <init_SLED>/database/strong_lenses_database.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
```
where you need to replace <init_SLED> accordingly. These two commands can be ran again if you need to reset the database.

4. Type [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser window and access the server.


### Development workflow

1. Any changes you make in the Django files (within your cloned SLED_api repo) will automatically restart the server. 

2. Note that you can restore the database in its original form at any time using the two commands from step 3 above.

3. Note that you can restore the files (lens mugshots, imaging data, etc) by downloading the data from [this link]() and copying them at the same path in your system as before. You could also make your own backup.

4. Once happy with your changes, submit a pull request.


### Contact

If you are seeking help, write to <sled-help@amnh.org>.


### Acknowledgements

Please cite [Vernardos et al. 2024]() if you are using SLED in your work.

