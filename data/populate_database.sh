cd add_users
python populate_db.py

cd ../add_lenses/
python upload_lensed_quasars.py

cd ../add_data
python add_instruments_bands.py
python upload_initial_imaging.py
python upload_initial_spectra.py
python upload_initial_catalogues.py

cd ../add_users
python mini_give_access.py