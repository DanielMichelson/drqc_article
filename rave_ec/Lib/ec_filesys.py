#!/opt/baltrad/third_party/bin/python
'''
Copyright (C) 2015 The Crown (i.e. Her Majesty the Queen in Right of Canada)

This file is an add-on to RAVE.

RAVE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

RAVE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RAVE.  If not, see <http://www.gnu.org/licenses/>.
'''

## Migrated from BALTEX Radar Data Centre : rave_archivetools.py
## and the Odyssey Development Environment : odc_filesys.py
## Some of this stuff is _really_ old, and I'd have rewritten it if it didn't
#  do the job well enough.

## @file
## @author Daniel Michelson, Environment and Climate Change Canada
## @date 2015-12-17

import sys, os, time, string, datetime, re
import _raveio
import odim_source, rave_hexquant
from Proj import rd

ECROOT     = '/opt/ec' # CHANGE where necessary
ECLIB      = ECROOT + '/Lib'
ECSRC      = ECROOT + '/src'
ECBIN      = ECROOT + '/bin'
ECDATA     = ECROOT + '/data'
ECETC      = ECROOT + '/etc'
INTERVAL   = 10
HINTERVAL  = INTERVAL / 2.0
RANGE      = range(0, 60, INTERVAL)

#ACQ_DELAY = 48*60*60    # how long we wait before fetching data: hours*min*secs
ACQ_DELAY = 0       # how long we wait before fetching data: min*secs
UPDATE_FREQ = INTERVAL*60     # how often we fetch data, in seconds
DAYS        = 14        # how many days of data in the archive
ARCHIVE_LEN = (60**2)*24*DAYS # in seconds/hour * hours * days


## Adds the appropriate daylight argument to a given time tuple
# @param time tuple generated with time.gmtime()
# @returns time tuple adjusted for daylight
def add_daylight(t):
    l = list(t)
    l[8] = -1
    return tuple(l)


## Bins minutes into intervals defined by 'interval'
# @param int minutes after the hour
# @returns padded string representation of the begining minute of the interval
def GetMinutes(MIN, interval=INTERVAL):
#    RANGE = range(0, 60, interval)
    for i in range(len(RANGE)):
        if i<len(RANGE)-1:
            if MIN >= RANGE[i] and MIN < RANGE[i+1]: mi = str(RANGE[i]).zfill(2)
        elif i==len(RANGE)-1:
            if MIN >= RANGE[i] and MIN < RANGE[i]+interval: mi = str(RANGE[i]).zfill(2)
    return mi


## Derives seconds somehow, for some reason. Currently unused.
# @param time tuple
# @returns epoch seconds (UNADJUSTED BY ACQ_DELAY) which are rounded to the 
# nearest acquisition interval.
def GetSeconds(t=None):
    if t == None:
        t = time.time()
        t = time.localtime(t)
    MIN = t[4]
    mi = int(GetMinutes(MIN))
    t = time.mktime((t[0], t[1], t[2], t[3], mi, 0, t[6], t[7], t[8]))
    return t


## Creates a time tuple adjusted by the time delay used for production.
# returns the archive time as a time tuple which can be fed to GetTimeTuple.
def GetTime():
    t = time.gmtime(time.time() - ACQ_DELAY)
    return add_daylight(t)


## Makes a time tuple representing the current time, including the time delay used for production.
# @returns time info down to the minute, given a time tuple
def GetTimeTuple(t=GetTime()):
    #t = add_daylight(t)
    return time.strftime("%Y", t), \
	   time.strftime("%m", t), \
	   time.strftime("%d", t), \
	   time.strftime("%H", t), \
	   time.strftime("%M", t)


## Creates a path to the file system given a date in the form YYMMDDHHmm as a string.
# @param string YYMMDDHHmm
# @returns full path
def time2path(t):
    YY, MM, DD, HH, mm = t[0:2], t[2:4], t[4:6], t[6:8], t[8:10]
    if eval(YY) > 90:
	YY = "19"+YY
    else:
	YY = "20"+YY
    return ECDATA+"/"+YY+"/"+MM+"/"+DD+"/"+HH+"/"+mm+"/"


## Creates a path to the file system given a time tuple.
# @param time tuple
# @returns the path for the given time (a time tuple)
def GetPathFromTuple(t):
    yr, mo, da, hr, mi = GetTimeTuple(t)
    MIN = int(mi)
    mi = GetMinutes(MIN)
    YR = os.path.join(ECDATA, yr)
    MO = os.path.join(YR, mo)
    DA = os.path.join(MO, da)
    HR = os.path.join(DA, hr)
    MI = os.path.join(HR, mi+"/")
    return MI


## Creates a path to the file system given a time in epoch seconds.
# @param time in epoch seconds, or nothing
# @returns the path for the given time (in seconds) or the most
# recent time if no argument is given.
def GetPath(t=None):
    if t:
	t = time.gmtime(t - ACQ_DELAY)
    else:
	t = time.gmtime(time.time() - ACQ_DELAY)
    return GetPathFromTuple(t)


## Makes a path to the file system given a time tuple.
# @param time tuple 
# @returns a path for the given time
def MakePathFromTuple(t):
    yr, mo, da, hr, mi = GetTimeTuple(t)
    MIN = int(mi)
    mi = GetMinutes(MIN)
    YR = os.path.join(ECDATA, yr)
    if not os.path.isdir(YR): os.mkdir(YR)
    MO = os.path.join(YR, mo)
    if not os.path.isdir(MO): os.mkdir(MO)
    DA = os.path.join(MO, da)
    if not os.path.isdir(DA): os.mkdir(DA)
    HR = os.path.join(DA, hr)
    if not os.path.isdir(HR): os.mkdir(HR)
    MI = os.path.join(HR, mi+"/")
    if not os.path.isdir(MI): os.mkdir(MI)
    return MI


# THE FOLLOWING GetPaths TAKE t IN SECONDS

## Gets a path to the file system down to the hour
# @param epoch seconds
# @returns the path as far as the HR field
def GetHourPath(t):
    return GetPath(t)[:-3]


## Gets a path to the file system down to the day
# @param epoch seconds
# @returns the path as far as the DA field
def GetDayPath(t):
    return GetPath(t)[:-6]


## Gets a path to the file system down to the month
# @param epoch seconds
# @returns the path as far as the MO field
def GetMonthPath(t):
    return GetPath(t)[:-9]


## Creates a product file name based on epoch seconds and a quantity prefix.
# This probably needs a major rewrite.
# @returns the file name of a composite file, given a time in _seconds_ and
# a prefix denoting the type of composite: dbzh or rr
def MakeProductFileName(s, prefix='dbzh'):
    t = time.gmtime(s)
    yr, mo, da, hr, mi = GetTimeTuple(t)
    path = GetDayPath(s)

    MIN = int(mi)
    mi = GetMinutes(MIN)
    fstr= "%s_comp_%sT%sZ.h5" % (prefix, yr+mo+da, hr+mi)
    return os.path.join(path, fstr)


## Make a hex signature for the given polar payload, either a SCAN or a PVOL
# @param RaveIOCore object
# @returns hex string representing the quantitities found in the payload 
def makeHexQuant(rio):
    if rio.objectType == _raveio.Rave_ObjectType_SCAN:
        quants = rave_hexquant.qFromScan(rio.object)
    elif rio.objectType == _raveio.Rave_ObjectType_PVOL:
        quants = rave_hexquant.qFromPvol(rio.object)
    return rave_hexquant.q2hex(quants)


## Rounds date and time to the nearest acquisition interval.
# @param string date in YYYYMMDD format
# @param string time in HHmmSS format
# @returns tuple containing date and time in the same format as input arguments
def RoundDT(DATE, TIME):
    tm = datetime.datetime(int(DATE[:4]), int(DATE[4:6]), int(DATE[6:8]),
                           int(TIME[:2]), int(TIME[2:4]), int(TIME[4:]))
    tm += datetime.timedelta(minutes=HINTERVAL)
    tm -= datetime.timedelta(minutes=tm.minute % INTERVAL,
                             seconds=tm.second,microseconds=tm.microsecond)
    return tm.strftime('%Y%m%d'), tm.strftime('%H%M%S')


## Creates a file name with complete path for a polar SCAN or PVOL
# @param RaveIOCore object
# @param boolean, whether to make the path if it doesn't already exist
# @returns string full path and file name
def MakePolarFileName(rio, root=ECROOT, makepath=False, Round=False):
    global ECDATA
    ECDATA = root
    s = odim_source.ODIM_Source(rio.object.source)

    if Round:
        DATE, TIME = RoundDT(rio.object.date, rio.object.time)
    else:
        DATE, TIME = rio.object.date, rio.object.time
    path = GetPathFromTuple((int(DATE[:4]), int(DATE[4:6]), int(DATE[6:8]),
                             int(TIME[:2]), int(TIME[2:4]), 0, 0, 0, 0))

    if makepath and not os.path.isdir(path):
        try:
            os.makedirs(path)
        except:
            sys.stderr.write('Warning: makedirs failed for %s\n' % path)

    fstr = os.path.join(path, s.nod)

    try:
        # Squash any empty spaces
        task = re.sub(" ", "", rio.object.getAttribute('how/task').lower())
    except AttributeError:
        task = None

    if task:
        fstr = '%s_%s' % (fstr, task)
        if rio.objectType == _raveio.Rave_ObjectType_SCAN:
            fstr = '%s_%2.1f' % (fstr, rio.object.elangle * rd)

    else:
        if rio.objectType == _raveio.Rave_ObjectType_SCAN:
            fstr = '%s_scan' % fstr
            fstr = '%s_%2.1f' % (fstr, rio.object.elangle * rd)

        elif rio.objectType == _raveio.Rave_ObjectType_PVOL:
            fstr = '%s_pvol' % fstr

    hexq = makeHexQuant(rio)

#    fstr = '%s_%sT%sZ.h5' % (fstr, DATE, TIME[:-2]) # Time the script is run.
#    fstr = '%s_%sT%s%sZ_%s.h5' % (fstr, DATE, TIME[:2], path.split("/")[-2], hexq)
    fstr = '%s_%sT%sZ_%s.h5' % (fstr, rio.object.date, 
                                rio.object.time[:4], hexq)
    return fstr


def MakeCompositeFileName(rio, root=ECROOT, prefix='comp_', makepath=False, Round=False):
    global ECDATA
    ECDATA = root
    if Round:
        DATE, TIME = RoundDT(rio.object.date, rio.object.time)
    else:
        DATE, TIME = rio.object.date, rio.object.time
    daypath = GetPathFromTuple((int(DATE[:4]), int(DATE[4:6]), int(DATE[6:8]),
                                int(TIME[:2]), int(TIME[2:4]), 0, 0, 0, 0))[:-7]
                                
    if makepath and not os.path.isdir(daypath): os.makedirs(daypath)
    
    fstr = "%s%sT%sZ.h5" % (prefix, DATE, TIME[:-2])
    return os.path.join(daypath, fstr)


## Purges files in the file system older than 'howold'
# @param root directory string
# @param time in epoch seconds representing 'now', from when to count backwards
# @param seconds * minutes * hours of age. Older files and directories than this will be purged.
def PurgeFilesys(rootdir=ECDATA, when=None, howold=60*60*24):
    if when == None:
        when = time.time()  # Now 
    for root, dirs, files in os.walk(rootdir, topdown=False):
        for name in files:
            fullpath = os.path.join(root, name)
            if os.stat(fullpath).st_mtime < when - howold:
                #print "Would rm %s" % fullpath
                try:
                    os.remove(fullpath)
                except:
                    pass
        for name in dirs:
            fullpath = os.path.join(root, name)
            if os.stat(fullpath).st_mtime < when - howold:
                #print "Would rmdir %s" % fullpath
                try:
                    os.rmdir(fullpath)
                except:
                    pass
                    print "Failed to purge directory %s" % fullpath


if __name__ == "__main__":
    print __doc__
