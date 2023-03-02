#!/bin/bash
# This script is run daily but AFTER the monthly backup script

readonly BACKUP_DIR=$1"/FILES"
readonly BACKUP_DATABASE_DIR=$1"/database"
readonly SOURCE_DIR=$2"/FILES"
cnf_file=$2"/launch_server/server_production.cnf"
MYSQLDUMP=$(which mysqldump)
AWK=$(which awk)

readonly TARGET="$(date '+%0d')"



########## BACKUP DATABASE ##########
# Get database connection parameters
MHOST=$($AWK '/^host/{print $3}' $cnf_file)
MPORT=$($AWK '/^port/{print $3}' $cnf_file)
MDB=$($AWK '/^database/{print $3}' $cnf_file)
MUSER=$($AWK '/^user/{print $3}' $cnf_file)
MPASS=$($AWK '/^password/{print $3}' $cnf_file)

# Full database backups using mysqldump
mysqldump -h $MHOST -P $MPORT -u $MUSER –p$MPASS $MDB > ${BACKUP_DATABASE_DIR}/${TARGET}.sql


########## BACKUP FILES ##########
# Incremental backups using rsync
set -o errexit
set -o nounset
set -o pipefail

readonly BACKUP_PATH=${BACKUP_DIR}/${TARGET}
readonly LATEST_LINK=${BACKUP_DIR}/latest

mkdir -p ${BACKUP_DIR}/${TARGET}

rsync -av --delete \
  "${SOURCE_DIR}/" \
  --link-dest "${LATEST_LINK}" \
  --exclude="temporary" \
  "${BACKUP_PATH}"

rm -rf "${LATEST_LINK}"
ln -s "${BACKUP_PATH}" "${LATEST_LINK}"
