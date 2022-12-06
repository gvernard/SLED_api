First off, you’ll need the files (images/jsons/paper csvs etc.). So I’ve put them on observatory filesystem and you can just copy them across, while in the base SLED directory:

scp USERNAME@login01.astro.unige.ch://home/astro/lemon/SLED_files/data_files.zip ./data/images_to_upload/
cd data/images_to_upload/
unzip -o -q data_files.zip
rm data_files.zip

cd ../..
scp USERNAME@login01.astro.unige.ch://home/astro/lemon/SLED_files/paper_files.zip ./data/add_papers/
cd ./data/add_papers/
unzip -o -q paper_files.zip
rm paper_files.zip

Now you can initialise the database. Go into initialise_database and run the reset_and_populate.sh script. The database should not be running when starting this script. You will be prompted to start the database after a few seconds, when data ingestion is about to start.

cd initialise_database
./reset_and_populate.sh