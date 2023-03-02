#!/bin/bash


# Set other values
spd="/opt/djangoapps/sled"
backup_dest="/projects/astro/sled/BACKUP"


# Activate SLED environment
eval "$(conda shell.bash hook)"
if [ `hostname -s` = "django01" ]
then
    conda activate /projects/astro/sled/SLED_environment
else
    conda activate SLED_environment
fi


# Set environment variables
export DJANGO_SLACK_API_TOKEN=`cat ${spd}/launch_server/slack_api_token.txt`
if [ `hostname -s` == "django01" ]
then
    export DJANGO_SECRET_KEY=`cat ${spd}/launch_server/secret_key.txt`
    export DJANGO_EMAIL_PASSWORD=`cat ${spd}/launch_server/email_password.txt`   
    export DJANGO_DOMAIN_NAME=sled.astro.unige.ch
fi



###################### Programs ran by cron ######################
# Fetch new avatars
python ${spd}/SLED_api/manage.py shell < fetch_new_avatars.py


# Run the monthly backup script
./monthly_backup.sh $backup_dest


# Run the daily backup script
./daily_backup.sh $backup_dest $spd
