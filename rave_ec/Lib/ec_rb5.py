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
# Reads Selex-Gematronik Rainbow 5 files into Toolbox (ODIM) representation.


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2015-12-07

import os
import numpy
import ec_RB_io
import _raveio
import _polarvolume
import _polarscan 
import _polarscanparam
from rave_defines import UTF8
import odim_source
from Proj import dr, rd
#from aifc import data
#from _rave import scan
#from scipy.optimize._tstutils import fstrings


NAME2SOURCE = {"KING_CAX01" : "caxka",
               "KING_CAX02" : "caxkb"}

# File string parameter name, ODIM Quantity, gain, offset, undetect, nodata
QGOUN = {"dBZ" : ("DBZH", 0.5, -32.0, 0.0, 255.0)}


## Determines if a given file is in RB5 format
#  @param string name of the input file
#  @returns Python boolean
def isRB5(filename):
    fd = open(filename)
    s = fd.read(7)
    fd.close()
    return s == '<volume'


def readRBScanParameter(filename):
    rb =  ec_RB_io.read_Rainbow(filename)['volume']

    rbquant =  rb['scan']['slice']['slicedata']['rawdata']

    param = _polarscanparam.new()
    param.quantity, param.gain, param.offset, param.undetect, param.nodata = QGOUN[rbquant['@type']]

    startangle=rb['scan']['slice']['slicedata']['rayinfo'][0]['data']
    start_az_index = numpy.argmin(startangle)

    mydata = rbquant['data']
    
    # Sort data according to azimuth angles, starting with the lowest angle from North, assuming clockwise ...
    if start_az_index != 0:
        begin = mydata[start_az_index:len(startangle)] 
        end = mydata[:start_az_index]
        mydata = numpy.concatenate((begin,end))
    
    param.setData(mydata)

    return rb, param


def makeScanFromRB(rb):
    scan = _polarscan.new()

    scan.date = str(rb['@datetime'][:4]+rb['@datetime'][5:7]+rb['@datetime'][8:10])
    scan.time = str(rb['@datetime'][11:13]+rb['@datetime'][14:16]+rb['@datetime'][17:19])

    scan.beamwidth = float(rb['sensorinfo']['beamwidth']) * dr
    scan.elangle = float(rb['scan']['pargroup']['posele']) * dr
    scan.rscale = float(rb['scan']['slice']['rangestep']) * 1000.0

    return scan


def makePvolFromFiles(filenames):
    pvol = _polarvolume.new()

    for fstr in filenames:
        rb, param = readRBScanParameter(fstr)
        scan = makeScanFromRB(rb)
        scan.addParameter(param)
        pvol.addScan(scan)

    pvol.sortByElevations(1)

    scan = pvol.getScan(0)
    pvol.date, pvol.time = scan.date, scan.time
    pvol.longitude = float(rb['sensorinfo']['lon']) * dr
    pvol.latitude = float(rb['sensorinfo']['lat']) * dr
    pvol.height = float(rb['sensorinfo']['alt'])

    try:
        nod = NAME2SOURCE[rb['sensorinfo']['@name']] 
    except KeyError:
        nod = None
    if nod:
        source = odim_source.SOURCE[nod]
        pvol.source = source.encode(UTF8)

    return pvol
        

def main(filename):
    try:
        i = filename.index('dBZ')
        
        rb, param = readRBScanParameter(filename)
        scan = makeScanFromRB(rb)
        scan.addParameter(param)
        
        return scan
    except ValueError:
        pass


if __name__=="__main__":
    pass
