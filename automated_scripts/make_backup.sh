#!/bin/bash
MYSQLDUMP=$(which mysqldump)
AWK=$(which awk)
current_path=`pwd`
secret_path=${current_path}/../../SLED_secrets



########## SETUP TARGET DIRECTORY ##########
if [[ $# -eq 1 ]]
then
    readonly NAME=$1
else
    readonly NAME="latest"
fi

readonly BACKUP_DIR="/var/tmp/SLED_tmp_backups/"${NAME}
mkdir -p ${BACKUP_DIR}
mkdir -p ${BACKUP_DIR}/database
mkdir -p ${BACKUP_DIR}/files

#if [ -d $BACKUP_DIR ]
#then
#    echo "A directory with the name - $NAME - already exists."
#    while true; do
#	read -p " Proceeding will overwrite it. Are you sure you want to proceed (y/n)? " yn
#	case $yn in
#            [Yy]* ) mkdir -p ${BACKUP_DIR}; mkdir -p ${BACKUP_DIR}/database; mkdir -p ${BACKUP_DIR}/files; break;;
#            [Nn]* ) exit;;
#            * ) echo "Please answer yes (y) or no (n).";;
#	esac
#    done
#else
#    mkdir ${BACKUP_DIR}; mkdir ${BACKUP_DIR}/database; mkdir ${BACKUP_DIR}/files
#fi



########## BACKUP DATABASE ##########

# Get database connection parameters
cnf_file=${secret_path}/sled_ro.cnf
if ! [ -f $cnf_file ]
then
    echo "File $cnf_file not found!"    
    exit
fi
MHOST=$($AWK '/^host/{print $3}' $cnf_file)
MPORT=$($AWK '/^port/{print $3}' $cnf_file)
MDB=$($AWK '/^database/{print $3}' $cnf_file)
MUSER=$($AWK '/^user/{print $3}' $cnf_file)
MPASS=$($AWK '/^password/{print $3}' $cnf_file)

# Full database backup using mysqldump
$MYSQLDUMP --single-transaction -h $MHOST -P $MPORT -u $MUSER -p$MPASS $MDB > ${BACKUP_DIR}/database/strong_lenses_database.sql





########## TRANSFER TO REMOTE BACKUP ##########

# Transfer backup file to remote backup storage
conf_file=${secret_path}/rclone.conf
if ! [ -f $conf_file ]
then
    echo "File $conf_file not found!"    
    exit
fi

S3_BACKUP_BUCKET_NAME=`grep -o 'Bucket.*' ${secret_path}/s3_backup.txt | cut -f2- -d: | tr -d ' '`
rclone --config="${conf_file}" move ${BACKUP_DIR} sled_backup:${S3_BACKUP_BUCKET_NAME}/${NAME}

S3_STORAGE_BUCKET_NAME=`grep -o 'Bucket.*' ${secret_path}/s3_storage.txt | cut -f2- -d: | tr -d ' '`
rclone --config="${conf_file}" sync sled_storage:${S3_STORAGE_BUCKET_NAME}/files sled_backup:${S3_BACKUP_BUCKET_NAME}/${NAME}/files



########## REMOVE LOCAL BACKUP DIR ############
rm -r ${BACKUP_DIR}
