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
## Validation of command-line arguments
# 


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-05-20

import os, errno

# errno gives positive exit status, we need a few others
EOK  = 0   # All OK
ERT  = -1  # Run-time error
EIFF = -2  # Illegal file format


## Validates an input file string  
# @param string of input file, with or without a path
# @returns tuple containing (modified) file string and exit code
def validateIfile(fstr):
    if fstr == None:
        return fstr, errno.EINVAL
    
    if os.path.split(fstr)[0] == '':
        fstr = os.path.abspath(fstr)
    
    if not os.path.isfile(fstr):
        print "Input file %s is not a regular file. Exiting ..." % fstr
        return fstr, errno.ENOENT
        
    if os.path.getsize(fstr) == 0:
        print "Input file %s is zero length. Exiting ..." % fstr
        return fstr, errno.EIO
    
    return fstr, EOK


## Validates an output file string  
# @param string of output file, which must have a valid path
# @returns int exit code
def validateOfile(fstr):
    opath = os.path.split(fstr)[0] 
    if opath == '':
        print "Full path to output file missing. Exiting ..."
        return errno.EINVAL
    else:
        if not os.path.isdir(opath):
            try:
                os.makedirs(opath)
            except OSError:
                print "Output path %s does not exist and cannot be created. Exiting ..." % opath
                return errno.ENOTDIR
        else:
            if not os.access(opath, os.W_OK):
                print "Read-only output path %s. Exiting ..." % opath
                return errno.EROFS
    return EOK




if __name__=="__main__":
    pass
