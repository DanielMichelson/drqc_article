#!/usr/bin/python
'''base script for work sequence: convert, QC, composite
'''
import gzip
import os
import multiprocessing
import shutil
# import stat
import sys
import time
import datetime
from shutil import rmtree
from shutil import copy
from shutil import copytree

# from config import verifroot
from config import dir_tmp_gunzip    # for *{CONVOL,DOPVOL2}*.gz
from config import dir_working

func_convert_CA = '%s/rave/bin/ecWxR_precipet' % os.getenv('RAVEROOT')
func_convert_US = '%s/rave/bin/ecWxR_convert' % os.getenv('RAVEROOT')

sequential = False


def timestamp():
    return datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')


def selectFiles(flist, ipath, ymdhm):
    # adapted from /fs/site1/dev/eccc/mrd/armp/bha001/dbm001/ssm/baltrad_18.08_ubuntu-14.04-amd64-64/rave/Lib/ecWxR_qc.py
    # Get nominal date and time for this set of files
    year, month, day, hour, minute = ymdhm[:4], ymdhm[4:6], ymdhm[6:8], ymdhm[8:10], ymdhm[10:12]
    nominal = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
    # nominal = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))

    d = {}
    for filename in flist:
        x = filename.split('_')
        # Ignore single scans that are length 5
        # e.g., usdyx_vcp32_0.5_20160701T0403Z_0x700002.usdyx.h5
        if len(x) == 4:
            node, tm = x[0], x[2]  # node is radar identifier
            if node not in d.keys():
                d[node] = filename
            else: # this is a new file
                tm_new = tm[:8]+tm[9:13]   # 20160731T2358Z
                newfiletime = datetime.datetime.strptime(tm_new, '%Y%m%d%H%M')
                tm = d[node].split('_')[2]
                tm_existing = tm[:8]+tm[9:13]
                existingfiletime = datetime.datetime.strptime(tm_existing, '%Y%m%d%H%M')
                # print abs(newfiletime - nominal), abs(existingfiletime - nominal)
                if abs(newfiletime - nominal) < abs(existingfiletime - nominal):
                    d[node] = filename
    l = []
    for k, i in d.items():
        l.append(i)
        
    return l


def worker_convert(input):
    '''
    '''
    dir_odimH5, fnames = input
    if len(fnames) == 2:    # a CONVOL/DOPVOL2 gzipped IRIS pair
        try:
            tmp_fname0 = fnames[0].split('/')[-1][:-3]
            tmp_fname1 = fnames[1].split('/')[-1][:-3]
            tmp_inPathFilename0 = '%s/%s' % (dir_tmp_gunzip, tmp_fname0)
            tmp_inPathFilename1 = '%s/%s' % (dir_tmp_gunzip, tmp_fname1)
            with gzip.open(fnames[0], 'rb') as f_in, open(tmp_inPathFilename0, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            with gzip.open(fnames[1], 'rb') as f_in, open(tmp_inPathFilename1, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            bash_cmd = '%s -i %s,%s -l %s' % (func_convert_CA,
                    tmp_inPathFilename0, tmp_inPathFilename1, dir_odimH5)
            os.system(bash_cmd)
            os.remove(tmp_inPathFilename0)
            os.remove(tmp_inPathFilename1)
        except:
            sys.stderr.write('Error: convert file %s\n' % fnames)
    elif len(fnames) == 1:    # a nexrad file
        try:
            bash_cmd = '%s -i %s -o * -l %s' % (func_convert_US,
                    fnames[0], dir_odimH5)
            os.system(bash_cmd)
        except:
            sys.stderr.write('Error: convert file %s\n' % fnames)


def convert(ymdhm=None):
    dir_ymdhm = dir_working+'/'+ymdhm
    dir_odimH5 = dir_ymdhm + '/odimH5'
    if os.path.isdir(dir_odimH5):
        rmtree(dir_odimH5)
    os.mkdir(dir_odimH5)
    fnames = []
    with open('%s/raw_%s.txt' % (dir_ymdhm, ymdhm), 'rb') as f:
        for line in [x.strip() for x in f.readlines()]:
            if line[-5:] == '.ar2v':
                fnames.append([line])
            elif line[-3:] == '.gz' and 'CONVOL' in line:
                # initialize_working.py pairs CONVOL and DOPVOL2
                fnames.append([line, line.replace('CONVOL', 'DOPVOL2')])
    inputs = [[dir_odimH5, x] for x in fnames]

    if sequential:
        for input in inputs:
            worker_convert(input)
    else:
        pool = multiprocessing.Pool()
        outputs = pool.map(worker_convert, inputs)
        pool.close()
        pool.join()


def worker_quality_control(input):
    dir_qc, inPathFname = input
    func = '%s/rave/bin/ecWxR_qc' % os.getenv('RAVEROOT')
    try:
        fname = inPathFname.split('/')[-1]
        part = fname.split('.')
        # fname has radar ID as part[1], and ecWxR_qc inserts it just before .h5'
        outFname = part[0]+'.qc.'+part[2]
        bash_cmd = '%s -i %s -o %s -l %s' % (func, inPathFname, outFname, dir_qc)
        os.system(bash_cmd)
    except:
        sys.stderr.write('Error: ecWxR_qc file %s\n' % inPathFname)


def quality_control(ymdhm=None):
    dir_ymdhm = dir_working+'/'+ymdhm
    ymdhm_slash = ymdhm[:4]+'/'+ymdhm[4:6]+'/'+ymdhm[6:8]+'/'+ymdhm[8:10]+'/'+ymdhm[10:12]
    dir_odimH5 = dir_ymdhm + '/odimH5'
    # any caxti files in bucket 10 minutes later omitted
    dir_odimH5_slash = dir_odimH5+'/'+ymdhm_slash
    dir_qc = dir_ymdhm + '/qc'
    os.mkdir(dir_qc)

    # reduce list to only one nominal file per radar per bucket
    flist = os.listdir(dir_odimH5_slash)
    flist_subset = selectFiles(flist, dir_odimH5_slash, ymdhm)
    fnames = ['%s/%s' % (dir_odimH5_slash, x) for x in flist_subset]
    inputs = [[dir_qc, x] for x in fnames]

    if sequential:
        for input in inputs:
            worker_quality_control(input)
    else:
        pool = multiprocessing.Pool()
        outputs = pool.map(worker_quality_control, inputs)
        pool.close()
        pool.join()
    # XXX gaps in composites? why do bunches of  radars go missing,
    # XXX it should not be due to premature removal of converted files:
    # rmtree(dir_odimH5)    # save space, work with 5 TB quota


def composite(ymdhm=None):
    dir_ymdhm = dir_working+'/'+ymdhm
    ymdhm_slash = ymdhm[:4]+'/'+ymdhm[4:6]+'/'+ymdhm[6:8]+'/'+ymdhm[8:10]+'/'+ymdhm[10:12]
    dir_qc = dir_ymdhm + '/qc'
    dir_qc_slash = dir_qc+'/'+ymdhm_slash
    dir_composite = dir_ymdhm+'/'+'composite'
    os.mkdir(dir_composite)
    func = '%s/rave/bin/ecWxR_composite' % os.getenv('RAVEROOT')
    oFname = 'qcomp_%s.h5' % ymdhm    # Dominik's scripts expect qcomp_
    time_arg = '%sT%sZ' % (ymdhm[0:8], ymdhm[8:12])
    try:
        bash_cmd = '%s -i %s/* -o %s -l %s -t %s -a gemNA' % (
                func, dir_qc_slash, oFname, dir_composite, time_arg)
        os.system(bash_cmd)
    except:
        sys.stderr.write('Error: ecWxR_composite could not generate %s\n' % oFname)


def store(ymdhm=None):
    from config import dir_store
    from config import dir_done
    pathWorking = dir_working+'/'+ymdhm
    ymdhm_slash = ymdhm[:4]+'/'+ymdhm[4:6]+'/'+ymdhm[6:8]+'/'+ymdhm[8:10]+'/'+ymdhm[10:12]
    if ymdhm[-2:] == '00':
        src = '%s/qc/%s' % (pathWorking, ymdhm_slash)
        dst = dir_store+'/'+ymdhm
        copytree(src, dst)
    ymd_slash = ymdhm_slash[0:-6]
    src = '%s/composite/%s/qcomp_%s.h5' % (pathWorking, ymd_slash, ymdhm)
    if os.path.isfile(src):
        dir_dst = '%s/q_comp/%s' % (dir_store, ymd_slash)
        if not os.path.isdir(dir_dst):
            os.makedirs(dir_dst)
        dst = '%s/qcomp_%s.h5' % (dir_dst, ymdhm)
        copy(src, dst)
    rmtree(pathWorking+'/odimH5')    # save space, work with 5 TB quota
    rmtree(pathWorking+'/qc')
    rmtree(pathWorking+'/composite')

    # this as last step limits number of nodes used at once;
    # July-August has 8928 time bins, after a long run 30 composites were not made
    # ran fix_gaps.py to find missing times and reset ./working directory
    # then reran launch_cycle.py
    pathDone = dir_done+'/'+ymdhm
    if os.path.isdir(pathDone):
        sys.stderr.write('Warning: done directory exists, being replaced, %s\n' % pathDone)
        rmtree(pathDone)
    os.rename(pathWorking, dir_done+'/'+ymdhm)


def update_status(pathStatus=None, step=None):
    with open(pathStatus, 'a') as f:
        f.write('%s %s\n' % (step, timestamp()))


# NOTE below sleep(60) was due to incomplete radar processing
# and *guess* that is was due to a file I/O issue, of os.listdir() not being current;
# however, processing became more complete with change in ec_filesys.py MakePolarFileName()
# of adding try/except, see around line 250 in
# /fs/site1/dev/eccc/mrd/armp/bha001/dbm001/ssm/baltrad_18.08_ubuntu-14.04-amd64-64/rave/Lib/ec_filesys.py

def process_raw(ymdhm=None, pathStatus=None):
    update_status(pathStatus=pathStatus, step=0)
    convert(ymdhm=ymdhm)
    update_status(pathStatus=pathStatus, step=1)
    time.sleep(60)  # NOTE maybe this can be deleted ?
    quality_control(ymdhm=ymdhm)
    update_status(pathStatus=pathStatus, step=2)
    time.sleep(60)  # NOTE maybe this can be deleted ?
    composite(ymdhm=ymdhm)
    update_status(pathStatus=pathStatus, step=3)
    store(ymdhm=ymdhm)
    pathStatus = pathStatus.replace('working','done')  # XXX
    update_status(pathStatus=pathStatus, step=4)

if __name__ == "__main__":
    for ymdhm in sys.argv[1:]:
        pathStatus = '%s/%s/status' % (dir_working, ymdhm)
        if os.path.isfile(pathStatus) and os.stat(pathStatus).st_size == 0:
             process_raw(ymdhm=ymdhm, pathStatus=pathStatus)
         # else:
         #     pass
         #     # no file means it's gone already,
         #     # or size != 0 means while this job waited in queue for over an hour, another job took and started this ymdhm
