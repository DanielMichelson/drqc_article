'''global configuration variables for package 
'''


from datetime import datetime, timedelta

verifroot = '/home/bha001/src'
dir_raw = '/space/hall1/sitestore/eccc/mrd/rpndat/dja001/data/us_can_vol_scans/cases'
dir_tmp_gunzip = '/fs/home/fs1/eccc/mrd/armp/bha001/tmp'    # temp dir used when gunzipping IRIS data
dir_working = '/space/hall1/sitestore/eccc/mrd/armp/bha001/data/radar/working'
dir_done = '/space/hall1/sitestore/eccc/mrd/armp/bha001/data/radar/done'
dir_store = '/space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar/store'

# range of dates processed, inclusive; to manage with quota limit of 5T in hall1
date_start = '20160701'
date_end = '20160901'
# date_end = '20160708'    # XXX
time_step_bin_size = 600    # files are grouped into ten-minute bins

# stages = ['raw', 'odimH5', 'qc', 'npz']    # stages of individual radar files


dt = dt_0 = datetime.strptime(date_start, '%Y%m%d')
dt_1 = datetime.strptime(date_end, '%Y%m%d')
time_step = timedelta(seconds=time_step_bin_size)    # bin size

date_start_minus_one = (dt_0 - timedelta(days=1)).strftime('%Y%m%d')
S_ymdhm = set()
while dt < dt_1:
    ymdhm = dt.strftime('%Y%m%d%H%M')
    S_ymdhm.add(ymdhm)
    dt += time_step


# first, initialize_working.py once to fix working directories
# then each call to launch_job.sh processes next yyyymmddhhmm/
#     in order of preference
#         an older timed out *'ing, to resume, if > one hour old
#         next raw in sequence 
#
# each call of launch_job.sh sets one node to working

# NOTE 5TB quota each in hall1 and hall2
