#!/bin/sh
# was missing HAC files for June, so simply copied July's to June's
cd /fs/site1/dev/eccc/mrd/armp/bha001/dbm001/baltrad/share/hac/data
for fname_july in `ls -1 201607_ca*hdf`
do
    fname_june="201606_`echo $fname_july | cut -c8-`"
    cp $fname_july $fname_june
done
