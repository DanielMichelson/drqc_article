#!/usr/bin/python
'''set up lists of files to process
   run once before starting a clean run from [date_start - date_end)
   this takes 10 minutes to prepare for July-August [20160701 - 20160901)
   this script depends on config.py and specified directories properly set up
'''
import os
import sys
from shutil import rmtree
from datetime import datetime, timedelta
from config import date_start, date_end, date_start_minus_one
from config import verifroot
from config import dir_raw
from config import dir_working
from config import dir_done
from config import dir_store
from config import time_step_bin_size
from config import S_ymdhm

ten_minutes = timedelta(seconds=600)
def ymdhm_plus_10(ymdhm):
    dt = datetime.strptime(ymdhm, '%Y%m%d%H%M')
    dt += ten_minutes
    return dt.strftime('%Y%m%d%H%M')


def initialize_working():
    '''
    '''
    for directory in [dir_working, dir_done, dir_store]:
        if not os.path.isdir(directory):
            sys.stderr.write('Error: directory does not exist, %s\ # ensure place to store resultsnEnsure that required directories with storage exist, then rerun.\n' % directory)
            sys.exit(1)

    for subd in ['q_comp', 'npz', 'emet']: # ensure place to store results
        dir_subd = dir_store+'/'+subd
        if not os.path.isdir(dir_subd):
            os.mkdir(dir_subd)
    for subd in ['TH', 'DBZH', 'RADAR_OBS_DISTANCE', 'RADAR_OBS_DISTANCE', 'RADAR_OBS_HEIGHT']:
        dir_subd = dir_store+'/emet/'+subd
        if not os.path.isdir(dir_subd):
            os.mkdir(dir_subd)

    time_step_half = timedelta(seconds=time_step_bin_size/2)
    for ymdhm in sorted(S_ymdhm):
        if os.path.isdir(dir_done+'/'+ymdhm):
            rmtree(dir_done+'/'+ymdhm)
        path_working = dir_working+'/'+ymdhm
        if os.path.isdir(path_working):
            rmtree(path_working)
        os.mkdir(path_working)
    for ymd in sorted(os.listdir(dir_raw)):
        if (len(ymd) != 8 or not ymd.isdigit()
                or not date_start_minus_one <= ymd < date_end):
            continue
        D_ymdhm = {x: [] for x in S_ymdhm}
        dir_ymd = dir_raw+'/'+ymd
        for stn in sorted(os.listdir(dir_ymd)):
            if len(stn) != 4 or not stn.isupper():
                continue
            dir_ymd_stn = dir_ymd+'/'+stn
            if stn[0] == 'C':
                for fname_convol in [x for x in sorted(os.listdir(dir_ymd_stn))
                        if x[14:20] == 'CONVOL' and x[-3:] == '.gz']:
                    ymdhm = fname_convol[0:12]
                    if ymdhm in S_ymdhm:
                        fname_dopvol = fname_convol.replace('CONVOL', 'DOPVOL2')
                        if os.path.isfile(dir_ymd_stn+'/'+fname_dopvol):
                            D_ymdhm[ymdhm].extend([
                                    dir_ymd_stn+'/'+fname_convol,
                                    dir_ymd_stn+'/'+fname_dopvol])

                            # HACK XSI metadata consistently had valid time ~ + 10 min
                            #   based on metadata compared to filename
                            if fname_convol[25:28] == 'XTI':
                                ymdhm = ymdhm_plus_10(ymdhm)
                                if ymdhm in S_ymdhm:
                                    D_ymdhm[ymdhm].extend([
                                            dir_ymd_stn+'/'+fname_convol,
                                            dir_ymd_stn+'/'+fname_dopvol])
            elif stn[0] in ['K', 'P']:
                for fname in [x for x in sorted(os.listdir(dir_ymd_stn))
                        if x[0:4].isupper() and x[-5:] == '.ar2v'
                        and x[4:12].isdigit() and x[13:19].isdigit()]:
                    dt = datetime.strptime(fname[4:12]+fname[13:19], '%Y%m%d%H%M%S')
                    # assign to 10-minute bucket: *4:59 down, *5:00 up
                    # freq nexrad each 6 min, so each bin gets one < 5 minutes off
                    dt += time_step_half    # + five minutes
                    ymdh = dt.strftime('%Y%m%d%H')
                    minute = int(dt.strftime('%M'))
                    ymdhm = ymdh + '%02d' % (minute - minute % 10)
                    if ymdhm in S_ymdhm:
                        D_ymdhm[ymdhm].append(dir_ymd_stn+'/'+fname)

        # for each time bucket, status value coordinates processing
        for ymdhm in D_ymdhm:
            d = D_ymdhm[ymdhm]
            if d:
                with open('%s/%s/raw_%s.txt' % (dir_working, ymdhm, ymdhm), 'a') as f:
                    for pathFile in sorted(d):
                        f.write('%s\n' % pathFile)
    with open(verifroot+'/flag_working', 'w') as f:
        f.write('0\n')

if __name__ == '__main__':
    initialize_working()
