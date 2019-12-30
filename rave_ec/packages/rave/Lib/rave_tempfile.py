'''
Copyright (C) 2010- Swedish Meteorological and Hydrological Institute (SMHI)

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
## Redefines the tempfile template for RAVE.

## @file
## @author Daniel Michelson, SMHI
## @date 2010-07-19

import sys, os, tempfile

# Use $TASK_WORK from Maestro and assume it exists
if os.getenv("TASK_WORK"):
    tempfile.tempdir = os.getenv("TASK_WORK")
# If no $TASK_WORK, try $BLT_USER_PATH/tmp
elif os.getenv("BLT_USER_PATH"):
    tempfile.tempdir = os.getenv("BLT_USER_PATH") + '/tmp'
    if not os.path.isdir(tempfile.tempdir):
        os.makedirs(tempfile.tempdir)
else:
    print "No path for temporary files given. Please specify $TASK_WORK (Maestro) or $BLT_USER_PATH. Exiting ..."
    sys.exit(127)

## The redefined template.
RAVETEMP = tempfile.tempdir


## RAVE's tempfile constructor.
# @param suffix string, can be e.g. '.h5' for HDF5 files
# @param close string, set to "True" to close the file before continuing.
# The default value is "False".
# @return tuple containing an int containing an OS-level handle to an open
# file as would be returned by os.open(), that can be closed with os.close().,
# and a string containing the absolute pathname to the file.
# NOTE the file is created and opened. In order to prevent too many open files,
# you may have to close this file before continuing.
def mktemp(suffix='', close=False):
    PREFIX = "rave%d-" % os.getpid()
    t = tempfile.mkstemp(prefix=PREFIX, suffix=suffix)
    if eval(close):
        os.close(t[0])
    return t



if __name__ == "__main__":
    print __doc__
