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
# Plugins containing useful data processing functionality, primarily for
# North American data. 
#

## 
# @file
# @author Daniel Michelson, Environment and Climate Change Cananda
# @date 2016-06-10

import _rave, _raveio, _polarvolume
import ec_dopvolqc

from rave_quality_plugin import rave_quality_plugin


class ec_dopvolFilter_plugin(rave_quality_plugin):
    ##
    # Default constructor
    def __init__(self):
        super(ec_dopvolFilter_plugin, self).__init__()
        self._option_file = None # Mostly for test purpose
    
    ##
    # @return a list containing the appropriate string
    def getQualityFields(self):
        return ["ca.ec.filter.dopvol-clutter"]

    ##
    # @param obj: A RAVE object that should be processed, always a PVOL in this case
    # @param reprocess_quality_flag: Not used here.
    # @param arguments: Comma-separated list of input DOPVOL file strings, assuming the order:
    #    dopvol1a, dopvol1b, dopvol1c, dopvol2
    # @return: obj - Filtered input object with associated quality field 
    def process(self, obj, reprocess_quality_flag=True, arguments=None):
        #_rave.setDebugLevel(_rave.Debug_RAVE_DEBUG)

        if not _polarvolume.isPolarVolume(obj):
            raise Exception, "Input object is not a polar volume. Bailing ..."

        # Using a dictionary lets us match tasks with payloads
        dpvol = {"dopvol1a" : None,
                 "dopvol1b" : None,
                 "dopvol1c" : None,
                 "dopvol2"  : None}

        for i in range(len(arguments)):
            dobj = _raveio.open(arguments[i]).object
            task = "".join(dobj.getAttribute('how/task').lower().split("_"))
            dpvol[task] = dobj 
        
        dopvol = ec_dopvolqc.mergeDopvol(dopvol1a = dpvol["dopvol1a"], 
                                         dopvol1b = dpvol["dopvol1b"],
                                         dopvol1c = dpvol["dopvol1c"],
                                         dopvol2  = dpvol["dopvol2"])

        # Assume we always want spatial=1 filtering
        ec_dopvolqc.dopvolFilter(obj, dopvol)
    
        return obj

    ##
    # @return: The distance information - dummy
    #
    def algorithm(self):
        return None
  
  
if __name__=="__main__":
    a = ec_quality_plugin()
