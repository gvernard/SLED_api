#!/bin/bash
# This script is run daily BEFORE the daily backup script

readonly BACKUP_DIR=$1"/FILES"
readonly BACKUP_DATABASE_DIR=$1"/database"
readonly DAY="$(date '+%0d')"
readonly yesterday="$(date -d 'yesterday' '+%Y%0m%0d')"


if [ $DAY != "01" ];then exit 0; fi


dum=`find ${BACKUP_DIR}/?? -type d -printf '%T@ %f\n' | sort -n | tail -1`
read time last_day_of_the_month <<< $dum

echo $last_day_of_the_month

if [ $last_day_of_the_month = 30 ] && [ -e ${BACKUP_DIR}/31 ]
then
    rm -r ${BACKUP_DIR}/31
    rm ${BACKUP_DATABASE_DIR}/31.sql
fi


cp ${BACKUP_DATABASE_DIR}/${last_day_of_the_month}.sql ${BACKUP_DATABASE_DIR}/${yesterday}.sql
cp -r ${BACKUP_DIR}/${last_day_of_the_month} ${BACKUP_DIR}/${yesterday}

# This is to force a new full backup from the daily backup script
rm -rf ${BACKUP_DIR}/latest

