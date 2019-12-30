#!/usr/bin/python
'''
Copyright (C) 2015 The Crown (i.e. Her Majesty the Queen in Right of Canada)

This file is an add-on to RAVE.

RAVE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RAVE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RAVE.  If not, see <http://www.gnu.org/licenses/>.

'''
##
# Processes data King X-band data deployed at OLYMPEX 
# for rave_gmaps


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2015-12-10

import sys, os, glob, time, re, xmlrpclib
import ec_rb5
import _raveio, _rave
import odc_polarQC

from compositing import compositing
from rave_defines import CENTER_ID, GAIN, OFFSET

DELAY = 60*10  # seconds x minutes

IROOT = '/data/dmichelson/olympex' 
DROOT = '/RADAR2/CAX1/REALTIME_FEED'
A = 'RAW_DOPVOL1_A'
B = 'RAW_DOPVOL1_B'
C = 'RAW_DOPVOL1_C'
OPATH = os.path.join(IROOT, 'pvol')
PPATH = os.path.join(IROOT, 'pcappi')
GPATH = "/data/dmichelson/rave_gmap/web/data/caxka_gmaps"
server = xmlrpclib.ServerProxy("http://localhost:8085/RAVE")
odc_polarQC.algorithm_ids = ["ropo","beamb"]

def generate(infiles, DATE, TIME):
    comp = compositing()
    comp.filenames = infiles.split(",")
    comp.detectors = odc_polarQC.algorithm_ids
    comp.quantity = "DBZH"
    comp.set_product_from_string("PCAPPI")
    #comp.range = options.range
    comp.gain = 0.5
    comp.offset = -32.0
    comp.prodpar = 1000.0
    comp.set_method_from_string("NEAREST_RADAR")
    comp.qitotal_field = None
    comp.pcsid = "gmaps"
    comp.xscale = 250.0
    comp.yscale = 250.0
    comp.zr_A = 200.0
    comp.zr_b = 1.6
    comp.applygapfilling = True
    comp.reprocess_quality_fields = True
    
    result = comp.generate(DATE, TIME, None)
    result.objectType = _rave.Rave_ObjectType_IMAGE

    rio = _raveio.new()
    rio.object = result
    
    ifstr = os.path.split(infiles)[1]
    ofstr = re.sub('pvol', 'pcappi', ifstr)
    ofstr = os.path.join(PPATH, ofstr)

    rio.save(ofstr)
    return ofstr


def gmaps(ifstr):
    rio = _raveio.open(ifstr)
    ofstr = GPATH + "/%s/%s/%s/%s.png" % (rio.object.date[:4], 
                                          rio.object.date[4:6], 
                                          rio.object.date[6:8],
                                          rio.object.date+rio.object.time[:-2])
    response = server.generate("se.smhi.rave.creategmapimage", [ifstr], ["outfile",ofstr])


def makeODIM():
    now = time.time()
    
    ifstrs = []
    Afiles = glob.glob(os.path.join(DROOT, A) + '/*dBZ.azi')
    Bfiles = glob.glob(os.path.join(DROOT, B) + '/*dBZ.azi')
    Cfiles = glob.glob(os.path.join(DROOT, C) + '/*dBZ.azi')
    allfiles = Afiles + Bfiles + Cfiles

    # Only bother with recent files
    for f in allfiles:
        if (now - os.path.getmtime(f)) < DELAY:
            ifstrs.append(f)
            print f
        
    pvol = ec_rb5.makePvolFromFiles(ifstrs)
    pvol = odc_polarQC.QC(pvol)
    
    rio = _raveio.new()
    rio.object = pvol
    DATE = pvol.date
    TIME = pvol.time
    
    ofstr = "%s/caxka_pvol_%sT%sZ.h5" % (OPATH, pvol.date, pvol.time)
    rio.save(ofstr)
    
    return ofstr, pvol.date, pvol.time
    


if __name__=="__main__":
    ifstr, DATE, TIME = makeODIM()
    ofstr = generate(ifstr, DATE, TIME)
    gmaps(ofstr)
