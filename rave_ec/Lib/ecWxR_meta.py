'''
Copyright (C) 2017 The Crown (i.e. Her Majesty the Queen in Right of Canada)

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
## Reads URP META file format.
#  Specific to PRECIP-ET output in polar coordinates.


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2017-04-25

import sys, os
import _raveio, _polarscan, _polarscanparam
import numpy as np
from Proj import dr

GAIN, OFFSET = 0.5, -32.0     # defaults from IRIS and URP
UNDETECT, NODATA = 0.0, 255.0


def readHeader(ALL):
    header = {}
    for line in ALL.split("\n"):
        if line[:11] == "TableLabels":
            break
        else:
            splitted = line.split(" ")
            key, item = splitted[0], splitted[1:]
            header[key] = item
    return header


def readMeta2Scan(filename):
    fd = open(filename)
    ALL = fd.read()

    scan = _polarscan.new()
    param = _polarscanparam.new()

    header = readHeader(ALL)
    nrays = int(header["Theta"][0])
    nbins = int(header["Range"][0])
    elangle = float(header["PPIAngle"][-1])
    longitude = float(header["LonCentre"][0])
    latitude = float(header["LatCentre"][0])
    height = float(header["GroundHeight"][0]) + float(header["HornHeight"][0])

    fd.seek(ALL.index("SizeInBytes"))
    line = fd.readline()
    BYTES = int(line.split(" ")[1])

    data = np.reshape(np.fromstring(ALL[-BYTES:], np.uint8), (nrays,nbins))
    data = np.where(np.equal(data, 1), 0, data)  # should be nodata but instead going with undetect

    fd.close()

    scan.elangle = elangle * dr
    scan.height = height
    scan.longitude = longitude * dr
    scan.latitude = latitude * dr

    param.gain, param.offset = GAIN, OFFSET
    param.undetect, param.nodata = UNDETECT, NODATA
    param.quantity = "DBZH"
    param.setData(data)

    scan.addParameter(param)

    return scan



if __name__=="__main__":
    pass
