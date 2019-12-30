#!/usr/bin/python
'''
Copyright (C) 2016 The Crown (i.e. Her Majesty the Queen in Right of Canada)

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
# Processes data from NEXRAD Level II and RUAD
# for rave_gmaps


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-01-06

import sys, os, glob, time, re, xmlrpclib
import _raveio, _rave, _polarvolume, _polarscan, _polarscanparam
import odc_polarQC
import ec_filesys
import rave_tempfile

from compositing import compositing
from rave_defines import CENTER_ID, GAIN, OFFSET

DELAY = 60*60  # seconds x minutes

GPATH = "/data/dmichelson/rave_gmap/web/data"
server = xmlrpclib.ServerProxy("http://localhost:8085/RAVE")
odc_polarQC.algorithm_ids = ["ropo","beamb"]


## Copys a parameter
# @param param input parameter to be copied
# @return new output parameter
def CopyParam(param):
    new = _polarscanparam.new()
    new.gain, new.offset = param.gain, param.offset
    new.nodata, new.undetect = param.nodata, param.undetect
    new.setData(param.getData())
    for attr in param.getAttributeNames():
        new.addAttribute(attr, param.getAttribute(attr))
    for i in range(param.getNumberOfQualityFields()):
        new.addQualityField(param.getQualityField(i))
    return new


## Back-up DBZH to TH and check that metadata are kosher.
#  @param pvol input polar volume
#  @return new output polar volume
def CopyDBZH(pvol):
    changed = False

    new = _polarvolume.new()
    new.date, new.time, new.source = pvol.date, pvol.time, pvol.source
    new.latitude, new.longitude = pvol.latitude, pvol.longitude
    new.height, new.beamwidth = pvol.height, pvol.beamwidth
    for attr in pvol.getAttributeNames():
        new.addAttribute(attr, pvol.getAttribute(attr))

    for i in range(pvol.getNumberOfScans()):
        scan = pvol.getScan(i)
        pnames = scan.getParameterNames()
        if "TH" in pnames and "DBZH" not in pnames:
            th = CopyParam(scan.getParameter("TH"))
            th.quantity = "DBZH"
            if th.nodata != 255.0: th.nodata = 255.0
            scan.addParameter(th)

        new.addScan(scan)
    return new



def generate(infiles, gain=GAIN, offset=OFFSET, scale=2000.0):
    comp = compositing()
    #comp.filenames = infiles.split(",")
    comp.detectors = odc_polarQC.algorithm_ids
    comp.quantity = "DBZH"
    comp.set_product_from_string("PCAPPI")
    #comp.range = options.range
    comp.gain = gain
    comp.offset = offset
    comp.prodpar = 1000.0
    comp.set_method_from_string("NEAREST_RADAR")
    comp.qitotal_field = None
    comp.pcsid = "gmaps"
    comp.xscale = scale
    comp.yscale = scale
    comp.zr_A = 200.0
    comp.zr_b = 1.6
    comp.applygapfilling = True
    comp.reprocess_quality_fields = True

    rio = _raveio.open(infiles)  # There is only one file ...
    pvol = rio.object

    # Copy TH to DBZH for all scans in this pvol
    pvol = CopyDBZH(pvol)

    # Save to tempfile
    tmpf = rave_tempfile.mktemp(suffix=".h5", close="True")
    rio.object = pvol
    rio.save(tmpf[1])
    comp.filenames = [tmpf[1]]

    DATE = rio.object.date
    TIME = rio.object.time
    
    try:
        result = comp.generate(DATE, TIME, None)
    except Exception, e:
        print "Error: %s" % e.__str__()
        print "removing %s" % tmpf[1]
        os.remove(tmpf[1])

    result.objectType = _rave.Rave_ObjectType_IMAGE

    result.source += ',NOD:%s' % getNode(pvol)

    rio = _raveio.new()
    rio.object = result
    
    path, ifstr = os.path.split(infiles)
    ofstr = re.sub('pvol', 'pcappi', ifstr)
    ofstr = os.path.join(path, ofstr)

    rio.save(ofstr)
    os.remove(tmpf[1])

    return ofstr


def getNode(obj):
   ids = obj.source.split(",")
   for ID in ids:
       k, v = ID.split(":")
       if k == "NOD": return v


def gmaps(ifstr):
    rio = _raveio.open(ifstr)
    NOD = getNode(rio.object)
    ofstr = "%s/%s_gmaps/%s/%s/%s/%s.png" % (GPATH, NOD,
                                             rio.object.date[:4], 
                                             rio.object.date[4:6], 
                                             rio.object.date[6:8],
                                             rio.object.date+rio.object.time[:-2])
    response = server.generate("se.smhi.rave.creategmapimage", [ifstr], ["outfile",ofstr])


if __name__=="__main__":
    ofstr = generate(sys.argv[1])
    gmaps(ofstr)
