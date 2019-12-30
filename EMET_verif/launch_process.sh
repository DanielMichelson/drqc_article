#!/bin/sh -x
# called by launch_cycle.py, with args $@
# so ord_soumet can be used,
# this script in turn calls process_radar.sh so BALRTAD can be used,
# and process_radar.sh in turn calls process_radar.py

# IMPORTANT: to manually halt cycle:
#   echo 1 > /home/bha001/src/flag_working

export VERIFROOT=/home/bha001/src

hostname=`hostname`
if [ "$hostname" == "eccc1-ppp1" ] ; then
    mach=ppp1
elif [ "$hostname" == "eccc1-ppp2" ] ; then
    mach=ppp2
else
  timestamp="`date -u +'%Y%m%d%H%M%S'`"
  echo "Error: unrecognized hostname $hostname" > $listingsPath/hostname_$timestamp
  exit 1
fi

# once bucket takes 4-5 minutes
# for one hour, 6 ten-minute buckets, 40 minutes should be enough
t=2400    # once bucket takes 4-5 minutes, 10 should be safe?
cpus=44
cm=200G
listingsPath=$VERIFROOT/listings

flag_working=`cat $VERIFROOT/flag_working`
if [ $flag_working -ne 0 ]; then
  exit 0
fi
ord_soumet $VERIFROOT/process_radar.sh -mach $mach -t $t -cpus $cpus -cm $cm -listing $listingsPath -shell bash -args $@
