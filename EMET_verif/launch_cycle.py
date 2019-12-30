#!/usr/bin/python
''' launch cycle of radar_processing, monitor queue to optimize

    to use this:
      have ~ 5 TB storage under /space/hall1/sitestore and /space/hall2/sitestore
      transient files saved under hall1, results saved to hall2
      to save a completely new set of results : 
        cd /space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar
        rm -rf store ; mkdir store ; mkdir store/qcomp

      see ~bha001/src (or equivilent if copied for other user)
      refer to config.py : the directories should be ready and available
      clear dir_working and dir_done
        cd /space/hall1/sitestore/eccc/mrd/armp/bha001/data/radar
        rm -rf working done ; mkdir working done
      cd ~bha001/src (or equivilent if copied for other user)

      fix [ date_start date_end ) range

   once : ./initialize_working.py
     scan archive of IRIS/NEXRAD, dir_raw
     make lists of files for each bucket in date range, e.g.,
     /space/hall1/sitestore/eccc/mrd/armp/bha001/data/radar/working
       201607010000
         raw_201607010000.txt

    once on ppp1
    cd ~/src ; rm -f nohup_1 ; nohup ./launch_cycle.py 1>nohup_1 2>&1 &
    once on ppp2
    cd ~/src ; rm -f nohup_2 ; nohup ./launch_cycle.py 1>nohup_2 2>&1 &

    result is ~ 1.3 TB under /space/hall2/sitestore/eccc/mrd/armp/bha001/data/radar/store

    8928 files took 65 h with 8 nodes ppp1/2 six buckets per call
    ___________________________________________________________________

    launch_cycle.py :
      determines args list of ymdhm buckets, passes downwards
      loops until working directory is empty
        launch_process.sh : calls ord_soumet properly, with args
            process_radar.sh args : controled by ord_soumet, has BALTRAD
                process_radar.py args :
                  for each ymdhm does convert, qc, composite, store subset
    ___________________________________________________________________

    NOTE : before using EMET, need to update metadata files for stns and radar
    see load_metadata.py , needs to be run with qualified dir_store
'''


import os
import stat
import sys
import time
from datetime import datetime, timedelta
from shutil import rmtree
import subprocess
# from pprint import pprint, pformat

from config import verifroot
from config import dir_working, dir_done

hostname = os.environ['HOSTNAME']
if hostname not in ['eccc1-ppp1', 'eccc1-ppp2']:
    sys.stderr.write("Error: unrecognized hostname, %s\n" % hostname)
    sys.exit(1)

dt_one_minute = timedelta(seconds=60)


def qstat():
    q = {'job': {}, 'nodes_free': 0}
    proc = subprocess.Popen(['r.qstat'], stdout=subprocess.PIPE)
    for ln in iter(proc.stdout.readline,''):
        # if ln[8:14] == 'end001':
        if ln[8:14] == 'bha001':    # XXX or other user
            q['job'][ln[:7]] = {
                    'name': ln[22:86].strip(),
                    'state': ln[87:90],  # Run, Que, Hel, Don
                    'submit_start': ln[92:107],
                    'time_elapsed': ln[108:116],
                    'cpus': ln[121:124].strip(),
                    'time_required': ln[140:148],
                    }
        elif ln[6:10] == 'Free':
            q['nodes_free'] = int(ln[34:37])
    return q


def print_qstat(q):
    sys.stderr.write('%s queue : %d\n' % (
            datetime.now().strftime('%Y/%m/%d %H:%M:%S'), len(q['job'])))
    for ID in sorted(q['job']):
        jb = q['job'][ID]
        sys.stderr.write('  %s %s %s %s %s %s %s\n' % (
            ID, jb['name'], jb['state'], jb['submit_start'],
            jb['time_elapsed'], jb['cpus'], jb['time_required']))


def sleep_period():
    ''' on ppp1 sleep til next 00/10/20/30/40/50 minute mark
        on ppp2 sleep til next 05/15/25/35/45/55 minute mark
    '''
    if hostname == 'eccc1-ppp1':
        mm = 0
    else:
        mm = 5
    dt = dt_now = datetime.utcnow()
    dt += dt_one_minute
    while dt.minute % 10 != mm:
        dt += dt_one_minute
    dt_later = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    time.sleep((dt_later - dt_now).seconds)


def ready_to_process(ymdhm, time_now):
    ''' determine if a ./working/ymdhm bucket is untouched yet or stale
    '''
    result = False
    pathWorking = '%s/%s' % (dir_working, ymdhm)
    pathFname = pathWorking+'/status'    # control file, monitors process progress

# FIXME
# this dir had already been done, saved
#   File "./launch_cycle.py", line 122, in ready_to_process
#   open(pathFname, 'wb').close()  # touch fresh directory
#   IOError: [Errno 2] No such file or directory: '/space/hall1/sitestore/eccc/mrd/armp/bha001/data/radar/working/201608271210/status'
# same for 201607041620 , done/201607041620/status had same mtime as nohup_1
# a file I/O synch issue, 1200 buckets processed before tripped
# lag between generation of L_ymdhm in calling function and below test,
# working/ymdhm was moved to done during lag

    if os.path.isdir(pathWorking): # this *should* always be true, by way of call
        if not os.path.isfile(pathFname):
            open(pathFname, 'wb').close()  # touch fresh directory
            result = True
        else:
            file_age = time_now - os.stat(pathFname)[stat.ST_MTIME]
            if file_age > 3600:    # a stale file from a terminated job
                # refresh directory and restart a Terminated job (ran too lonh, file I/O ?)
                sys.stderr.write('Warning : %s %d seconds old, restarting\n' % (
                    pathFname, file_age))    # XXX
                # TODO cd ~/listings ; grep seconds * # verify this resort works
                #   was not passed after 1200 dirs
                open(pathFname, 'wb').close()  # rewrite as empty
                for directory in ['odimH5', 'qc', 'composite']:
                    _path = pathWorking+'/'+directory
                    if os.path.isdir(_path):
                        rmtree(_path)
                result = True
    else:
        pathDone = '%s/%s' % (dir_done, ymdhm)
        if not os.path.isdir(pathDone):
            # unrecoverable, throw an Error at least, as pathWorking did exist
            # earlier during this module's run
            sys.stderr.write('Error : missing both %s %s: \n' % (
                    pathWorking, pathDone))    # XXX
    return result


if __name__ == "__main__":
    # using 10 nodes at a time worked, some users have 40 running for hours
    max_nodes = 8    # XXX experiment with this, increase outside of M-F 9-5 hours
                      # XXX with 20 and ppp1 and ppp2, 2 months processed in 19.5 hours
    args_per_node = 6    #  # six buckets per node
    time_start = time.time()
    num_buckets = len(os.listdir(dir_working))

    while True:
        L_ymdhm = os.listdir(dir_working)
        if not L_ymdhm:
            seconds_run = time.time() - time_start
            sys.stderr.write('%s Done!!!\n' %
                    datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
            sys.stderr.write('average ~ %d seconds per bucket ( %d / %d )\n' %
                    ((seconds_run / num_buckets), seconds_run, num_buckets))
            sys.exit(0)
        # like Chunnel ppp1, ppp2 dig towards middle from opposite ends
        if hostname == 'eccc1-ppp1':
            L_ymdhm = sorted(L_ymdhm)
        else:
            L_ymdhm = sorted(L_ymdhm, reverse=True)
        q = qstat()

        if __debug__:        # XXX
            print_qstat(q)   # XXX

        num_nodes = len(q['job'])

        # num_nodes = 8    # XXX
        
        if len(q['job']) >= max_nodes:
             # check again in ~ 10 minutes, time for file system to update enough
             sleep_period()
             continue
      
        ## num free nodes varies 4 - 80, don't ask for more than half at any one time
        ## as this script runs in background and this loop is passed every ten minutes
        ## number of nodes used grows during low-use times; this script releases a node
        ## after about half an hour, then requests more in next pass of this loop
        ## not "monopolizing" Science machines, but optimizing throughput of radar processing

        num_nodes_to_request = min(max_nodes - num_nodes, q['nodes_free'] / 2)
        if num_nodes_to_request == 0:
            sleep_period()
            continue

        max_args = num_nodes_to_request * args_per_node
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        time_now = time.time()
        L_args = []
        for ymdhm in L_ymdhm:
            if ready_to_process(ymdhm, time_now):
                L_args.append(ymdhm)
            if len(L_args) == max_args:
                break
            # RESUME submit in batches up to six long
        for i in range(0, len(L_args), args_per_node):
            cmd = ['%s/launch_process.sh' % verifroot]
            for ymdhm in L_args[i:i+args_per_node]:
                cmd.append(ymdhm)
            sys.stderr.write('%s %s\n' % (timestamp, cmd))
            # os.system(cmd)
            # subprocess.Popen(cmd, stdout=subprocess.PIPE)

            sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = sp.communicate()
            if out:
                sys.stdout.write('standard output of subprocess:\n%s\n' % out)
            if err:
                sys.stderr.write('standard error of subprocess:\n%s\n' % err)

        sleep_period()
