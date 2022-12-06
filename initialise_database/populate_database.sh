cd ../data/add_users/
python populate_db.py

cd ../add_lenses/
python upload_through_api.py

cd ../add_papers
python upload_papers_API.py

cd ../add_collections
python upload_collection.py

cd ../add_data
python add_instruments_bands.py
python upload_initial_imaging.py
python upload_initial_spectra.py
python upload_initial_catalogues.py
