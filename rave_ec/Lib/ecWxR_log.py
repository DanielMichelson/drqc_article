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
#  Centralized logging functionality


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-12-22

import logging, logging.handlers
from rave_pgf_logger import LOGLEVELS, LOGFILESIZE, LOGFILES
LOGLEVEL = logging.INFO
LOGROOT = '/fs/cetus/fs3/mrb/armp/armpdbm/etc'


## Convenience function. Initializes the logger.
# @param logger an instance returned by \ref logging.getLogger()
# @param level int log level
def init_logger(logger, logfile, level=LOGLEVEL, SIZE=LOGFILESIZE, FILES=LOGFILES):
    logger.setLevel(LOGLEVEL)
    if not len(logger.handlers):
        handler = logging.handlers.RotatingFileHandler(logfile,
                                                       maxBytes = LOGFILESIZE,
                                                       backupCount = LOGFILES)
        formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


## Returns an initialized logger for immediate use.
# @param string name for the logger
# @param string file name for the logger
def getLogger(NAME, FILE, LEVEL=LOGLEVEL, SIZE=LOGFILESIZE, FILES=LOGFILES):
    logger = logging.getLogger(NAME)
    init_logger(logger, FILE, LEVEL, SIZE, FILES)
    return logger



if __name__=="__main__":
    pass
