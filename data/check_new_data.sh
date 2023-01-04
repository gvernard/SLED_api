cd add_data

echo 'Checking for missing catalogue data'
python check_for_catalogues.py

echo 'Checking for missing spectra'
python check_for_spectra.py

echo 'Checking for missing imaging data'
python check_for_imaging.py