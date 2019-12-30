#!/usr/bin/env python
'''
Copyright (C) 2016 The Crown (i.e. Her Majesty the Queen in Right of Canada)

This file is an add-on to RAVE.

RAVE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RAVE and this software are distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RAVE.  If not, see <http://www.gnu.org/licenses/>.

'''
##
#  Limits the maximum range of (NEXRAD Level II) data to (250) km


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-12-06

import sys, os, glob, re
import multiprocessing
import _raveio
import _polarscan, _polarscanparam
import numpy as np
from Proj import rd


## Convenience function for copying scan attributes
# @param input PolarScan object
# @param output PolarScan object
def copyScanAttrs(scan, newscan):
    newscan.source = scan.source
    newscan.date = scan.date
    newscan.time = scan.time
    newscan.longitude = scan.longitude
    newscan.latitude = scan.latitude
    newscan.height = scan.height
    newscan.elangle = scan.elangle
    newscan.beamwidth = scan.beamwidth
    newscan.rscale = scan.rscale
    newscan.rstart = scan.rstart
    newscan.a1gate = scan.a1gate
    newscan.startdate = scan.startdate
    newscan.starttime = scan.starttime
    newscan.enddate = scan.enddate
    newscan.endtime = scan.endtime
    for aname in scan.getAttributeNames():
        val = scan.getAttribute(aname)
        newscan.addAttribute(aname, val)


## Generator that trims back data to a specified maximum range. Default behaviour is to read an input file
#  write an output file. Alternatively, a RaveIO object can be passed in memory.
# @param string of the input file
# @param int maximum range (km) to which to trim back data
# @param boolean whether to overwrite the input file
# @param boolean whether to write a file period
# @param list of strings containing which parameters to keep; others are ignored
# @param string part of the input file string to modify
# @param string format string for new output files
# @param RaveIO object of the input PVOL
# @returns string of the (new) output file, or output RaveIO object
def generate(fstr, maxr=250, overwrite=False, write=True, 
             PARAMS=['DBZH','TH','ZDR','RHOHV','VRADH'], 
             iqual='_qc_', oqual='_qc%i_', RIO=None):
    if RIO: rio = RIO
    else: rio = _raveio.open(fstr)
    pvol = rio.object

    scanlist, elangles = [], []

    # Save scans to list
    for i in range(pvol.getNumberOfScans()):
        scan = pvol.getScan(i)
        if scan.elangle not in elangles:
            scanlist.append(scan.clone())
            elangles.append(scan.elangle)
    # Remove all scans
    for i in range(pvol.getNumberOfScans()):
        pvol.removeScan(0)

    for scan in scanlist:
        maxbin = int(maxr*1000 / scan.rscale)
        existing_max = scan.nbins*scan.rscale/1000

        if maxr < existing_max:

            newscan = _polarscan.new()
            copyScanAttrs(scan, newscan)

            for pname in scan.getParameterNames():
                if pname in PARAMS:
                    param = scan.getParameter(pname).clone()
                    data = param.getData()
                    data = np.array(data[:,:maxbin], data.dtype)
                    param.setData(data)
                    scan.removeParameter(pname)
                    newscan.addParameter(param)

            for i in range(scan.getNumberOfQualityFields()):
                field = scan.getQualityField(i)
                data = field.getData()
                data = np.array(data[:,:maxbin], data.dtype)
                field.setData(data)
                newscan.addQualityField(field)

        else:
            newscan = scan
            for pname in newscan.getParameterNames():
                if pname not in PARAMS:
                    newscan.removeParameter(pname)

        pvol.addScan(newscan)

    filename = rio.filename
    rio = _raveio.new()
    rio.filename = filename
    rio.object = pvol

    if RIO:
        return rio

    if not overwrite:
        rio.filename = re.sub(iqual, oqual % maxr, rio.filename)

    if write:
        rio.save()

    return rio.filename


## Parallelized trimmer
# @param list of input file strings
# @returns list of output file strings
def multi_generate(file_list):
    pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)

    results = []
    r = pool.map_async(generate, file_list, chunksize=1, callback=results.append)
    r.get()

    pool.terminate()
    pool.join()
    del pool

    return results[0]


if __name__=="__main__":
    l = multi_generate([sys.argv[1]])
    print l
