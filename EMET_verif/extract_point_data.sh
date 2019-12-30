#!/bin/sh -x
export VERIFROOT=/home/bha001/src
. ssmuse-sh -d /fs/site1/dev/eccc/mrd/armp/bha001/dbm001/ssm
export BLT_USER_PATH=/fs/site1/dev/eccc/mrd/armp/bha001/dbm001/baltrad
$VERIFROOT/extract_point_data.py

