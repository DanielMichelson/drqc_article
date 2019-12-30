#!/usr/bin/python
'''after running "nohup launch_cycle.py", for July-August 2016
    *hould* have 8928 h5 files under /space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar/store/q_comp
    but found about 24 were missing, guess due to file transfer issues;
    solution was to run this script (to update the working directory)
    and to run nohup launch_cycle.py once again (it worked)
'''

import os
from shutil import copyfile
from shutil import rmtree

from config import dir_working
from config import dir_done
from config import dir_store
from config import S_ymdhm

dir_qcomp = dir_store+'/q_comp'

missing = []

for ymdhm in sorted(S_ymdhm):
    pathFname = '%s/%s/%s/%s/qcomp_%s.h5' % (
            dir_qcomp, ymdhm[:4], ymdhm[4:6], ymdhm[6:8], ymdhm)
    if not os.path.isfile(pathFname):
        missing.append(ymdhm)


for ymdhm in missing:
    pathStore = dir_store+'/'+ymdhm
    if os.path.isdir(pathStore):
        rmtree(pathStore)
    pathWorking = dir_working+'/'+ymdhm
    if not os.path.isdir(pathWorking):
        os.mkdir(pathWorking)
    fname = 'raw_%s.txt' % ymdhm
    pathDone = dir_done+'/'+ymdhm
    copyfile(pathDone+'/'+fname, pathWorking+'/'+fname)


print 'reset working directories: %s' % missing
print 'rerun launch_cycle.py'
