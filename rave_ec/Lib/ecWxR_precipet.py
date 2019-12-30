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
## Shell-escapes URP's PRECIP-ET and reads in the result from META file
# 


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2017-04-26

import sys, os
import _rave, _raveio
import _iris2odim
import ecWxR_meta


def precipET(convol_fstr, dopvol2_fstr, ofstr):
    if os.path.isfile(convol_fstr) and \
       os.path.isfile(dopvol2_fstr):
        try:
            PETBIN = os.environ["URPDIR"] + "/bin/URPPrecipET -ms -i %s %s -o %s -k RADAR:*:PRECIPET,125,8,MPRATE_QPE,PRECIPET_QC_PARAMETERS:DUMB:DUMB:META"
            os.system(PETBIN % (convol_fstr, dopvol2_fstr, ofstr))
        except KeyError:
            print "$URPDIR environment variable not set"
    if os.path.isfile(ofstr) and os.path.getsize(ofstr):
        return True
    else:
        return False


## Merges PRECIP-ET scan with CONVOL scan, correcting metadata if necessary
# @param scan CONVOL
# @param scan PRECIP-ET scan
def mergePET(cscan, pscan):
    # Check scan-level metadata
    if cscan.elangle != pscan.elangle: cscan.elangle = pscan.elangle
    if cscan.height != pscan.height: cscan.height = pscan.height
    if cscan.longitude != pscan.longitude: cscan.longitude = pscan.longitude
    if cscan.latitude != pscan.latitude: cscan.latitude = pscan.latitude

    if cscan.nrays != pscan.nrays or cscan.nbins != pscan.nbins:
        raise IOError, "mergePET: Polar geometries do not match"

    dbzh = pscan.getParameter("DBZH")
    cscan.addParameter(dbzh)


if __name__=="__main__":
    pass
