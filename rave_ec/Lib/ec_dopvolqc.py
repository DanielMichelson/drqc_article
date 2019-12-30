'''
Copyright (C) 2016 The Crown (i.e. Her Majesty the Queen in Right of Canada)

This file is part of RAVE.

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
#  Quality controls reflectivity data using radial wind data collected separately.


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-04-04

import sys
import _rave, _raveio
import _polarvolume
import _polarscanparam
import _ravefield
from Proj import dr, rd
import numpy


## Merges Doppler scans into a volume
# @param scan containing DOPVOL1_A
# @param scan containing DOPVOL1_B
# @param scan containing DOPVOL1_C
# @param scan containing DOPVOL2
# @returns pvol containing all available scans
def mergeDopvol(dopvol1a=None, dopvol1b=None, dopvol1c=None, dopvol2=None):

    # Create a new ascending volume
    pvol = _polarvolume.new()
    if dopvol1a: pvol.addScan(dopvol1a)
    if dopvol1b: pvol.addScan(dopvol1b)
    if dopvol1c: pvol.addScan(dopvol1c)
    if dopvol2:  pvol.addScan(dopvol2)

    # Carry over top-level metadata from whichever DOPVOL is available
    if dopvol1a: obj = dopvol1a
    elif dopvol1b: obj = dopvol1b
    elif dopvol1c: obj = dopvol1c
    elif dopvol2: obj = dopvol2
    pvol.date = obj.date
    pvol.time = obj.time
    pvol.source = obj.source
    pvol.beamwidth = obj.beamwidth
    pvol.latitude = obj.latitude
    pvol.longitude = obj.longitude
    pvol.height = obj.height
    pvol.addAttribute("how/task", "DOPVOL")

    return pvol


## Performs clutter filtering of CONVOL data using DOPVOL data.
#  The closest DOPVOL scan to a given CONVOL scan is used, even if
#  the closest matching DOPVOL elevation angle isn't very close. 
#  Because the polar geometries of the CONVOL and DOPVOL scans can be 
#  different, polar-to-polar transformation is performed. The use of 
#  a spatial kernel is optionally/preferrably used to account for 
#  precipitation drift during the time it takes to acquire all data. 
#  This is fairly primitive, with the polar kernel being hardwired 
#  according to the known geometries:
#  360 or 720 expected rays,
#  500 or 1000 meter bins.
#  The radial wind threshold is also fixed to be 2 * Nyquist / 127 ,
#  because we use 8-bit uchar data to represent VRADH.
#  Data quality is characterized in a rudimentary way, related to 
#  the proportion of radial wind values in the polar kernel. Fewer
#  values will give lower qualities.
#  @param pvol containing CONVOL data 
#  @param pvol containing DOPVOL data 
#  @param int whether to perform spatial filtering, 1=yes
def dopvolFilter(convol, dopvol, spatial=1):
    import _rave_ec

    if not dopvol.isAscendingScans(): dopvol.sortByElevations(1)
    
    for i in range(convol.getNumberOfScans()):
        cscan = convol.getScan(i)
        dscan = dopvol.getScanClosestToElevation(cscan.elangle, 0)

        # These attributes require setting when pulling out a scan
        dscan.longitude = cscan.longitude
        dscan.latitude = cscan.latitude
        dscan.height = cscan.height

        if not _rave_ec.dopvolFilter(cscan, dscan, spatial):
            raise Exception, "dopvolFilter failed"


## DEPRECATED: prototype managing the DOPVOL filter 
# @param pvol containing CONVOL data
# @param pvol containing DOPVOL data
def dopvolQC(convol, dopvol):
    if not dopvol.isAscendingScans(): dopvol.sortByElevations(1)
    
    for i in range(convol.getNumberOfScans()):
        cscan = convol.getScan(i)
        dscan = dopvol.getScanClosestToElevation(cscan.elangle, 0)

        # These attributes require setting when pulling out a scan
        dscan.longitude = cscan.longitude
        dscan.latitude = cscan.latitude
        dscan.height = cscan.height
        
        DBZH, qfield = QC(cscan, dscan, SPATIAL=True)
        cscan.addQualityField(qfield)
        cscan.addParameter(DBZH)


## DEPRECATED: prototype of the actual DOPVOL filter 
# @param scan containing CONVOL data
# @param scan containing DOPVOL data
# @param boolean whether to perform spatial filtering
# @returns two-tuple containing filtered reflectivity and quality indicator field 
def QC(cscan, dscan, SPATIAL=True):
    gain = 1.0 / 256
    TH = cscan.getParameter("TH")
    VRADH = dscan.getParameter("VRADH")
    cscan_copy = cscan.clone()
    DBZH = cscan_copy.getParameter("TH")
    DBZH.quantity = "DBZH"  # Rename TH to DBZH
    qfield = _ravefield.new()
    qdata = numpy.zeros((DBZH.nrays, DBZH.nbins), numpy.uint8) + 255
    qfield.setData(qdata)
    qfield.addAttribute('what/gain', gain)  # Change gain and offset to 1 if we want binary [1,0] quality "flag"
    qfield.addAttribute('what/offset', 0.0)
    qfield.addAttribute('how/task', 'ca.ec.filter.dopvol-clutter')
    #qfield.addAttribute('how/task_args', 'None')
    #step = dscan.getAttribute('how/NI') * 2 / 253  # Assumes 8-bit data
    ni = dscan.getAttribute('how/NI')  # Nyquist interval
    print ni / 127.0, cscan.elangle*rd, dscan.elangle*rd, dscan.getAttribute('how/task')
    vthresh = 2 * ni / 127.0  # Wind threshold below which echoes are assumed to be static

    for r in range(cscan.nrays):
        for b in range(cscan.nbins):
            convol_vtype, convol_val = TH.getConvertedValue(b, r)

            # Only process data, not nodata or undetect
            if convol_vtype is _rave.RaveValueType_DATA:  
                lon, lat = cscan.getLonLatFromIndex(b, r) # Gives radians
                vtype, vval = dscan.getNearestConvertedParameterValue(VRADH.quantity, (lon,lat))

                # Set zero velocities to undetect in DBZH
                if SPATIAL == False:
                    if vtype is not _rave.RaveValueType_DATA:
                        DBZH.setValue((b, r), DBZH.undetect)
                        qfield.setValue(b, r, 0)  # Zero quality, showstopper
                    else:
                        if abs(vval) <= vthresh:
                            DBZH.setValue((b, r), DBZH.undetect)
                            qfield.setValue(b, r, 0)  # Zero quality, showstopper

                else:
                    # Optionally loop over a 3x3 kernel in dscan, remember to pad arrays!
                    BR = dscan.getNearestIndex((lon, lat))  # Will return None if out of bounds
                    if BR: 
                        BIN, RAY = BR
                    else:
                        #print "Bailing at ray %i, bin %i" % (r, b)
                        #DBZH.setValue((b, r), DBZH.nodata)
                        continue
    
                    # Deal with radial wrap-around
                    if 0 < r < VRADH.nrays: rayrange = range(RAY-1, RAY+2)
                    elif r == VRADH.nrays-1: rayrange = (VRADH.nrays-2, VRADH.nrays-1 ,0)
                    elif r == 0: rayrange = (VRADH.nrays-1, 0, 1)
    
                    hits, sum, n = 0, 0.0, 0
                    for i in rayrange:
                        for j in range(BIN-1, BIN+2):
                            if 0 <= j < VRADH.nbins: 
                                n += 1
                                vtype, vval = VRADH.getConvertedValue(j, i)
                                if vtype is _rave.RaveValueType_DATA:
                                    hits += 1
                                    sum += abs(vval)
                    # Calculate mean absolute radial wind speed and quality based on how many bins in the kernel
                    # have DATA in them. Alternative quality could weight the closest bin relative to the rest.
                    if hits > 0:
                        MEAN = sum / hits
                        quality = float(hits) / float(n)
                    else:
                        MEAN, quality = 0.0, 0.0 
                    if abs(MEAN) <= vthresh:
                        DBZH.setValue((b, r), DBZH.undetect)
                    #if convol_val < 7.0:  # Just to compare with the web graphic of PRECIPET
                    #    DBZH.setValue((b, r), DBZH.undetect)
                    qfield.setValue(b, r, quality / gain)  # We can have non-zero quality with values of UNDETECT                

    return DBZH, qfield


if __name__=="__main__":
    pass
