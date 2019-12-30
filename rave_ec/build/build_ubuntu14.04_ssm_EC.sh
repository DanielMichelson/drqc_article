#!/usr/bin/env bash
set -x

# Daniel Michelson, Observation Based Research Section, S&T Branch, Toronto
# 2018-01-12

## This script downloads, where relevant, and installs BALTRAD Toolbox 
## components, along with some dependencies where required.
## For use in CMC's Ubuntu 14.04 Science environment.
## Each package is defined in a function. Functions are called in order at the
## bottom of this script, and can be commented if necessary.

# The following line has the only path you need to edit
export ROOT=/ssm/net/cmoi/apps
export HD=~/bbuild
export SSMNAME=baltrad_19.07_ubuntu-14.04-amd64-64
export BLT=$ROOT/$SSMNAME
export ETC=$BLT/etc/profile.d
export SOURCE=$ETC/$SSMNAME.sh

# Define a bogus $BLT_USER_PATH because rb52odim uses it for unit testing
export BLT_USER_PATH=/home/vagrant/baltrad

if ! [ -d $ETC ]
then
mkdir -p $ETC
fi

# Create $SOURCE if it doesn't already exist
if ! [ -f $SOURCE ]
then
echo "if [[ ! \$RAVEROOT ]]; then" > $SOURCE
echo "export RAVEROOT=$BLT" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
fi
cd $HD/src

# HL-HDF: "our" original high-level API to HDF5. Makes things really easy.
function hlhdf {
git clone git://git.baltrad.eu/hlhdf.git
cd hlhdf
git checkout 218e46e96bfb572e3d93b98cfbc3d29635a1467e
./configure --prefix=$BLT/hlhdf
make
make test
make install
echo "echo \$PATH | grep -q \"hlhdf\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/hlhdf/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/hlhdf/lib\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/hlhdf/lib\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
cd $HD/src
}

# RAVE - BALTRAD Toolbox, the product generation framework
function rave {
git clone git://git.baltrad.eu/rave.git
cd rave
git checkout 38d4f519b6e9300b006928c84a731d7e0c150a38
# Comment unused packages so we don't have to install them
sed -i -e 's/import jprops/#import jprops/g' Lib/rave_bdb.py
sed -i -e 's/import jprops/#import jprops/g' Lib/rave_dom_db.py
sed -i -e 's/from keyczar import keyczar/#from keyczar import keyczar/g' Lib/BaltradFrame.py
sed -i -e 's/gtk.window_set_default_icon_from_file(RAVEICON)/#gtk.window_set_default_icon_from_file(RAVEICON)/g' Lib/rave_ql.py
./configure --prefix=$BLT/rave --with-hlhdf=$BLT/hlhdf --with-proj=/usr/include,/usr/lib --with-expat=/usr/include,/lib/x86_64 --with-numpy=/usr/lib/python2.7/dist-packages/numpy/core/include/numpy/
sed -i -e 's/-lproj/-lproj -lhdf5/g' librave/scansun/Makefile
make
make test
make install
echo "echo \$PATH | grep -q \"rave\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/rave/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/rave/lib\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/rave/Lib\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
cd $HD/src
}

# BEAMB - Toolbox package for beam blockage analysis and correction.
# External package because (a couple of) GTOPO30 tiles are included. 
# You must install additional tiles manually for North American coverage!
# Don't worry: we do it below.
function beamb {
git clone git://git.baltrad.eu/beamb.git
cd beamb
git checkout a2807593097717d6d875cf83fc176da603024274
./configure --prefix=$BLT/beamb --with-rave=$BLT/rave
make
make test
sed -i -e 's/BEAMBLOCKAGE_BBLIMIT= 1.1/BEAMBLOCKAGE_BBLIMIT= 0.6/g' pybeamb/beamb_quality_plugin.py
make install
echo "echo \$PATH | grep -q \"beamb\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/beamb/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/beamb/lib\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/beamb/share/beamb/pybeamb\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
grep -l beamb $BLT/rave/etc/rave_pgf_quality_registry.xml
if [ $? == 1 ]
then 
sed -i 's/<\/rave-pgf-quality-registry>/  <quality-plugin name="beamb" module="beamb_quality_plugin" class="beamb_quality_plugin"\/>\n<\/rave-pgf-quality-registry>/g' $BLT/rave/etc/rave_pgf_quality_registry.xml
fi
# Install GTOPO30 tiles that are not included in the stock release.
# This will fail if the GTOPO30 directory doesn't exist or is empty.
cd ../GTOPO30
if [ "$?" = "0" ]; then
    cp * $BLT/beamb/share/beamb/data/gtopo30/
else
    echo "No GTOPO30 directory, no tiles to copy..."
fi
cd $HD/src
}

# BROPO - Toolbox package for non-precip target identification and removal.
# External package because it's based on external legecy ROPO code from FMI.
function bropo {
git clone git://git.baltrad.eu/bropo.git
cd bropo/
git checkout 8dd8f0300bd5403ac3572e61126270f0aadefb27
./configure --prefix=$BLT/bropo --with-rave=$BLT/rave
make
make test
make install
echo "echo \$PATH | grep -q \"ropo\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/bropo/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/bropo/lib\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/bropo/share/bropo/pyropo\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
grep -l ropo_quality_plugin $BLT/rave/etc/rave_pgf_quality_registry.xml
if [ $? == 1 ]
then sed -i 's/<\/rave-pgf-quality-registry>/  <quality-plugin name="ropo" module="ropo_quality_plugin" class="ropo_quality_plugin"\/>\n<\/rave-pgf-quality-registry>/g' $BLT/rave/etc/rave_pgf_quality_registry.xml
fi
cd $HD/src
}

# BALTRAD WRWP - Toolbox package for generating vertical profiles. 
# External package due to external GPL dependencies (that we just built).
function wrwp {
git clone git://git.baltrad.eu/baltrad-wrwp.git
cd baltrad-wrwp/
git checkout f8062710ea5c1fc3dd7910101b1f89b4f229e153
./configure --prefix=$BLT/baltrad-wrwp --with-rave=$BLT/rave --with-blas=/usr/lib --with-cblas=/usr/lib --with-lapack=/usr/lib --with-lapacke=/usr/include,/usr/lib
make
make test
make install
echo "echo \$PATH | grep -q \"wrwp\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/baltrad-wrwp/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/baltrad-wrwp/lib\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/baltrad-wrwp/share/wrwp/pywrwp\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
cd $HD/src
}

# Seemingly unnecessary dependency: Imaging 1.1.7 (has since been fixed)
# Later versions of Ubuntu should be able to use stock Pillow. tbd...
function gmaps_dependencies {
wget --no-check-certificate http://git.baltrad.eu/blt_dependencies/Imaging-1.1.7.tar.gz .
tar xvzf Imaging-1.1.7.tar.gz
cd Imaging-1.1.7
sed -i -e 's/#include <freetype\//#include <freetype2\//g' _imagingft.c
cp ../etc/setup.py.Imaging-1.1.7-tweaked setup.py
python setup.py install --prefix=$BLT
echo "echo \$PYTHONPATH | grep -q \"PIL\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PATH=\"\$PATH:\$RAVEROOT/bin\"" >> $SOURCE
echo "export LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$RAVEROOT/lib/python2.7/site-packages/PIL\"" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/lib/python2.7/site-packages/PIL\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
cd $HD/src
}

# EXTRA BONUS: BALTRAD GoogleMapsPlugin! For creating snazzy radar displays
# using Google Maps.
function gmaps {
git clone git://git.baltrad.eu/GoogleMapsPlugin.git
cd GoogleMapsPlugin/
git checkout 8d240d8c0a947479068a4fb63227d937812bc15f
python setup.py install --prefix=$BLT  # Last step will fail; doesn't matter
echo "echo \$PYTHONPATH | grep -q \"gmap\"" >> $SOURCE
echo "if [ \$? == 1 ]; then" >> $SOURCE
echo "export PYTHONPATH=\"\$PYTHONPATH:\$RAVEROOT/rave_gmap/Lib\"" >> $SOURCE
echo "fi" >> $SOURCE
source $SOURCE
cd $HD/src
}

# Environment Canada extensions

# IRIS reader
function iris2odim {
git clone https://github.com/wmo-ipet-owr/iris2odim.git
cd iris2odim
git checkout 606074e7f16459d1ee45c7049acf641bec336700
make
make test
make install
cd $HD/src
}

# Rainbow 5 reader
function rb52odim {
git clone https://github.com/wmo-ipet-owr/rb52odim.git
cd rb52odim
git checkout c33915087f18365b80c86d72184c7ee5b4e36a0f
make
make test
make install
cd $HD/src
}

# Main project containing miscellaneous EC extensions and tweaks to packages
# already installed (above)
function ec {
export GIT_SSL_NO_VERIFY=1  # Because SSC ...
git clone --depth 1 https://gccode.ssc-spc.gc.ca/dbm/rave_ec.git
cd rave_ec
#make
#make test
make install
# Change the logo on the web front end.
cp config/index.php $BLT/rave_gmap/web/.
cp config/wmms.gif $BLT/rave_gmap/web/img/.
# Add Canadian and American radars to ODIM sources
cp config/odim_source.xml $BLT/rave/config/.
# Add Canadian S-band metadata to rb52odim
cp config/odim_radar_table.xml $BLT/rave/config/.
# Tweak some defaults for Canada
# Commented, file is added under 'packages'
#sed -i -e 's/GAIN = 0.4/GAIN = 0.5/g' $BLT/rave/Lib/rave_defines.py
#sed -i -e 's/OFFSET = -30.0/OFFSET = -32.0/g' $BLT/rave/Lib/rave_defines.py
#sed -i -e 's/ORG:82/ORG:53/g' $BLT/rave/Lib/rave_defines.py
#sed -i -e 's/LOGGER_TYPE="syslog"/LOGGER_TYPE="logfile"/g' $BLT/rave/Lib/rave_defines.py
# Copy tweaked files from rave/Lib instead
cp packages/rave/Lib/*.py $BLT/rave/Lib/
# Copy tweaked BEAMB plugin
cp packages/beamb/share/beamb/pybeamb/beamb_quality_plugin.py $BLT/beamb/share/beamb/pybeamb/.
# Add GEM-related projection and area.
cp config/projection_registry.xml $BLT/rave/config/.
cp config/area_registry.xml $BLT/rave/config/.
# Add new plugin(s)
#grep -l ec_dopvolFilter_plugin $BLT/rave/etc/rave_pgf_quality_registry.xml
#if [ $? == 1 ]
#then sed -i 's/<\/rave-pgf-quality-registry>/  <quality-plugin name="dopvolFilter" module="ec_quality_plugin" class="ec_dopvolFilter_plugin"\/>\n<\/rave-pgf-quality-registry>/g' $BLT/rave/etc/rave_pgf_quality_registry.xml
#fi
grep -l zdiff $BLT/rave/config/qitotal_options.xml
if [ $? == 1 ] ;
then sed -i 's/<\/qitotal>/    <field name="eu.opera.odc.zdiff" weight="1.0"\/>\n<\/qitotal>/g' $BLT/rave/config/qitotal_options.xml
fi
# Misc that's been tweaked
cp config/hac_options.xml $BLT/rave/config/.
cp config/qitotal_options.xml $BLT/rave/config/.
cp config/radvol_params.xml $BLT/rave/config/.
cp config/ropo_options.xml $BLT/bropo/share/bropo/config/.
cp etc/* $BLT/rave/etc/
# Add SSM stuff
cp -r .ssm.d $BLT/.
cd $HD/src
}

# Depolarization ratio functionality
function drqc {
git clone https://github.com/DanielMichelson/drqc.git
cd drqc
make
make test
make install
cd $HD/src
}

# Create SSM tarball, ignoring directories containing beamb tiles and look-ups
function tarball {
cd $ROOT
tar cvfzh $BLT.ssm $SSMNAME --exclude-tag-under=gtopo30 --exclude-tag-under=cache
cd $HD/src
}

# State which packages to install
hlhdf
rave
beamb
bropo
wrwp
gmaps_dependencies
gmaps
iris2odim
rb52odim
ec
drqc
tarball

#fin
