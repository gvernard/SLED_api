# DB_web
Web interface for the strong lens database

# Launching the database locally for development

1. Prerequisite: Install docker compose.
2. Download the initialization data from this link.
3. Copy the tarball anywhere in your system and note the path - we will call this path <init_SLED> from now on.
4. Untar and unzip
```sh
tar xvf init_SLED.tar.gz
```
5. Clone this repository anywhere in your system and note the path - we will call this path <SLED_api> from now on.
6. Locate the file docker_compose.yaml in the directory run_dev_server and replace the <init_SLED> and <SLED_api> with your actual paths.
7. In the same directory, run the following command:
```sh
docker compose up --build
```
This may take a while as various VMs and packages are being fetched.
If this command is successful, congratulations, you have an instance of SLED running!
8. The last thing left is to populate the database. Open a new terminal in the same directory and run
```
cat setup_db.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
cat <init_SLED>/database/strong_lenses_database.sql | docker exec -i SLED_database bash -c 'mysql -uroot -p${MYSQL_ROOT_PASSWORD} -D ${MYSQL_DATABASE}'
```
where you need to replace <init_SLED> accordingly. These two commands can be ran again if you need to reset the database.
9. Type http://127.0.0.1:8000/ in your browser window and access the server.
10. Any changes you make in the Django files (within your cloned SLED_api repo) will automatically restart the server. 
11. Once happy with your changes, submit a pull request.