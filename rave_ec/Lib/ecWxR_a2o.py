#!/usr/bin/python
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
## Reads IRIS, NEXRAD Level II, and McGill data from gzipped files, and writes ODIM_H5.
#  Does this traversing a file system of archived data.

## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-06-30

import sys, os, glob, string, traceback, datetime, mimetypes
import gzip
import _iris2odim
import ec_nexrad
import ec_mcgill
import ec_filesys
import _raveio
import rave_tempfile
import multiprocessing
import odim_source
import ecWxR_log
import ecWxR_trimRange
LOGGER_NAME = 'ecWxR_a2o'
LOGFILE = ecWxR_log.LOGROOT + '/ecWxR_a2o.log'

ROOTPATH = '/fs/cetus/fs3/mrb/armp/armpdbm'
INPATH = os.path.join(ROOTPATH, 'input')
OUTPATH = os.path.join(ROOTPATH, 'output')
TMPPATH = os.path.join(ROOTPATH, 'tmp/rave')
if not os.path.isdir(TMPPATH):
    try: os.makedirs(TMPPATH)
    except OSError: pass
rave_tempfile.tempfile.tempdir = TMPPATH
rave_tempfile.RAVETEMP = TMPPATH

IGNORE = []  # Already done


def gunzip(fstr):
    payload = gzip.open(fstr).read()
    path, fstr = os.path.split(fstr)
    fstr = os.path.join(TMPPATH, fstr[:-3])
    fd = open(fstr, 'w')
    fd.write(payload)
    fd.close()
    return fstr


## Use this only with Canadian CONVOL file strings to find matching DOPVOL file strings
# 
def getDopvols(cfstr, only_dopvol2=True):
    path, filename = os.path.split(cfstr)
    DT = filename[:12]
    if only_dopvol2:
        return glob.glob(os.path.join(path, DT+'*DOPVOL2*'))
    else:
        return glob.glob(os.path.join(path, DT+'*DOPVOL*'))


## Sanity check for dates that are one day earlier with times starting with 24
# @param pvol or scan object
def checkDT(obj):
    if obj.time[:2] == '24':
        DATE, TIME = obj.date, obj.time
        tm = datetime.datetime(int(DATE[:4]), int(DATE[4:6]), 
                               int(DATE[6:8]), 0, 
                               int(TIME[2:4]), int(TIME[4:]))
        tm += datetime.timedelta(hours=24)
        obj.date, obj.time = tm.strftime('%Y%m%d'), tm.strftime('%H%M%S')


def makeCanadianPvol(flist):
    from ec_quality_plugin import ec_dopvolFilter_plugin
    import ec_dopvolqc

    rio = _iris2odim.readIRIS(flist[0])
    convol = rio.object
    checkDT(convol)  # Sanity check on date/time

    dpvol = {"dopvol1a" : None,
             "dopvol1b" : None,
             "dopvol1c" : None,
             "dopvol2"  : None}

    if len(flist) > 1:
        for fstr in flist[1:]:
            dobj = _iris2odim.readIRIS(fstr).object
            task = "".join(dobj.getAttribute('how/task').lower().split("_"))
            dpvol[task] = dobj

        dopvol = ec_dopvolqc.mergeDopvol(dopvol1a = dpvol["dopvol1a"], 
                                         dopvol1b = dpvol["dopvol1b"],
                                         dopvol1c = dpvol["dopvol1c"],
                                         dopvol2  = dpvol["dopvol2"])

        try: ec_dopvolqc.dopvolFilter(convol, dopvol)
        except: pass  # Keep convol even if the filter fails
    rio.object = convol

    return rio


## Uses CONVOL and DOPVOL2 to generate a PRECIP-ET scan which is saved as a PVOL
#
#
def makeCanadianPETScan(flist):
    import ecWxR_precipet, ecWxR_meta
    from Proj import dr

    # First run PRECIP-ET
    meta_fstr = flist[0] + ".meta"  # Same file string with new extension
    if not ecWxR_precipet.precipET(flist[0], flist[1], meta_fstr):
        if os.path.isfile(meta_fstr): os.remove(meta_fstr)
        raise IOError, "ecWxR_precipet.precipET failed on %s" % flist[0]

    # Second, read the result and merge with lowest CONVOL sweep
    pet_scan = ecWxR_meta.readMeta2Scan(meta_fstr)
    rio = _iris2odim.readIRIS(flist[0])
    convol = rio.object
    beamw = convol.getAttribute('how/beamwH') * dr
    checkDT(convol)  # Sanity check on date/time
    convol.sortByElevations(1)
    convol_scan = convol.getScan(0).clone()
    ecWxR_precipet.mergePET(convol_scan, pet_scan)  # Will cast an IOError if it fails

    convol_scan.beamwidth = beamw
    convol.beamwidth = beamw

    while convol.getNumberOfScans():
        convol.removeScan(0)
    convol.addScan(convol_scan)

    rio.object = convol  # Now contains DBZH from PRECIP-ET
    if os.path.isfile(meta_fstr): os.remove(meta_fstr)

    return rio


## Converts to ODIM_H5. If Canadian IRIS files, perform dopvol-clutter filtering.
# @param fstrs list containing one Level II or McGill file, or several IRIS files
# @param trim boolean, whether to trim NEXRAD data (True) or not.
# @returns integer return code
def generate(flist, trim=True):
    try:

#        # Skip NEXRAD, K for CONUS, P for Alaska
#        if os.path.split(flist[0])[1][0] in ('K', 'P'):
#            return flist[0], "Skipped"

        files = []
        for fstr in flist:
            if mimetypes.guess_type(fstr)[1] == 'gzip':
                files.append(gunzip(fstr))
            else:
                files.append(fstr)

        path, fstr = os.path.split(files[0])

        # Is Canadian? Starts with digits, whereas NEXRAD LII files start with letters
        if fstr[0] in string.digits:
            # Is IRIS?
            if _iris2odim.isIRIS(files[0]):
                rio = makeCanadianPETScan(files)
                #rio = makeCanadianPvol(files)

            # Else is McGill
            else:
                rio = _raveio.new()
                rio.object = ec_mcgill.file2pvol(files[0])  # Should only be one file

        # Else is Level II
        else:
            rio = ec_nexrad.readLevelII(files[0])
            if trim:
                rio = ecWxR_trimRange.generate("bobbe", RIO=rio)  # dummy file string because it doesn't exist yet


        # Determine output file string
        ofstr = ec_filesys.MakePolarFileName(rio, root=OUTPATH, makepath=True, Round=True)
        rio.save(ofstr)

        # Clean up tmp directory
        for fstr in files:
            if os.path.split(fstr)[0] == TMPPATH: os.remove(fstr)

    except Exception, e:
        # Clean up tmp directory
        for fstr in files:
            if os.path.split(fstr)[0] == TMPPATH: os.remove(fstr)
        return flist, traceback.format_exc()

    return ofstr, "OK"


## Multiprocesses the generate function
# @param list of input file string lists, each list being one or more files
# @param trim boolean, whether to trim NEXRAD data (True) or not.
# @returns list of two-tuples containing output file names and return status
def multi_generate(file_lists, trim=False):
    if multiprocessing.cpu_count() == 16:
        pool = multiprocessing.Pool(16)  # Joule
    else:
        pool = multiprocessing.Pool(36)  # Everything else

    results = []
    r = pool.map_async(generate, file_lists, chunksize=1, callback=results.append)
    r.wait()

    pool.terminate()  # Being explicit
    del pool

    return results[0]
    


## Main process that loops through input directories and matches up files.
#  This creates a list of input file lists.
# @param string path to date (YYYYMMDD) input directory
# @param boolean, whether to process files concurrently (True) or not (False). If so, will multiprocess one day at a time.
# @param logging.logger object, optional
# @param list or None containing any of 'C' (Canada), 'K' (conus), and 'P' (Alaska)
# @param boolean, whether to trim NEXRAD data (True) or not.
def main(datepath, multiprocess=True, logger=None, IGNORE=None, trim=False):
        if os.path.isdir(datepath):
            FILE_LISTS = []
            #print datepath

            for sitepath in glob.glob(datepath + '/*'):
                if os.path.isdir(datepath):

                    # Determine ODIM node
                    path, site = os.path.split(sitepath)
                    if site[0] == 'C': sp = 'ca'
                    elif site[0] in ['K', 'P']: sp = 'us'
                    else: print site
                    node = sp+site[1:].lower()

                    try:
                        source = odim_source.SOURCE[node]
                    except KeyError:
                        print "Failed with %s" % site
                        
                    #print sitepath, source

                    # Canada - group each CONVOL together with its associated DOPVOLs
                    if sp == 'ca':
                        if site[0] not in IGNORE:
                            convols = glob.glob(os.path.join(sitepath, '*CONVOL*'))
                            for convol in convols:
                                dopvols = getDopvols(convol)  # Second arg True for DOPVOL2 only, False for all DOPVOLs
                                dopvols.sort()
                                dopvols.insert(0, convol)
                                FILE_LISTS.append(dopvols)

                    # USA - process each file individually
                    elif sp == 'us':
                        if site[0] not in IGNORE:
                            l2 = glob.glob(os.path.join(sitepath, '*'))
                            for l in l2:
                                FILE_LISTS.append([l])

                else:
                    print "%s is not a directory, ignoring ..." % sitepath
#            return FILE_LISTS
            # Concurrent processing
            if multiprocess:
                print "About to process %i files under %s" % (len(FILE_LISTS), datepath)
                if len(FILE_LISTS) > 0:
                    results = multi_generate(FILE_LISTS, trim)
                    if logger:
                        logger.log(ecWxR_log.LOGLEVEL, "%i files in %s. Exceptions follow:" % (len(FILE_LISTS), datepath))
                        for result in results:
                            if result[1] != 'OK':
                                logger.log(ecWxR_log.LOGLEVEL, "%s" % str(result))
            else:
                # Sequential processing
                for l in FILE_LISTS:
                    ofstr, status = generate(l)
                    print ofstr, status
        else:
            print "%s is not a directory, or just ignoring ..." % datepath


def getDirListing(fstr):
    fd = open(fstr)
    LINES = fd.readlines()
    fd.close()
    lines = []
    for line in LINES:
        if line[0] != '#':
            lines.append(line[:-1])
    return lines


if __name__ == "__main__":
    from optparse import OptionParser

    usage = "usage: %prog [-i <input dir> -f [file name] -I [ignore] -t [trim] -L [log file] -s [sequential processing]] [h]"

    parser = OptionParser(usage=usage)

    parser.add_option("-i", "--indir", dest="in_dir",
                      help="Name of input directory with files to process.")

    parser.add_option("-f", "--directory_listing_file", dest="dlf",
                      help="The look-up file containing input directories.")

    parser.add_option("-I", "--ignore", dest="ignore",
                      help='List of radar types to ignore. Can be either of C (Canada), K (conus), and P (Alaska), e.g. "C,K"')

    parser.add_option("-t", "--trim", dest="trim", action="store_true",
                      help='Trims the maximum range of NEXRAD data, according to presets in ecWxR_trimRange')

    parser.add_option("-L", "--logfile", dest="lfile",
                      default=LOGFILE,
                      help="Name of log file to write.")

    parser.add_option("-s", "--sequential", dest="seq",
                      action="store_true",
                      help="Process data sequentially, not concurrently. Defaults to True.")
  
    (options, args) = parser.parse_args()

    if options.lfile:
        logger = ecWxR_log.getLogger(LOGGER_NAME, options.lfile)
    else:
        logger = ecWxR_log.getLogger(LOGGER_NAME, LOGFILE)

    if options.ignore:
        IGNORE = options.ignore.split(',')
        if len(IGNORE) == 0: IGNORE = None

    if not options.trim:
        options.trim = False

    if options.in_dir:
        if os.path.isdir(options.in_dir):
            if options.seq:
                main(options.in_dir, False, logger, IGNORE, options.trim)
            else:
                main(options.in_dir, True, logger, IGNORE, options.trim)
        else:
            print "Invalid input directory: %s" % options.in_dir
                
    elif options.dlf:
        if os.path.isfile(options.dlf):

            paths = getDirListing(options.dlf)

            for path in paths:
                if options.seq:
                    main(path, False, logger, IGNORE, options.trim)
                else:
                    main(path, True, logger, IGNORE, options.trim)
        else:
            print "Invalid input file: %s" % options.dlf

    else:
        parser.print_help()
        sys.exit(-1)

