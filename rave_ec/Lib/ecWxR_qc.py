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
## Reads ODIM_H5 files and quality controls them.
#  Does this by reading a directory listing file and processing the data for each
#  input path in this listing.

## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-06-30

import sys, os, glob, traceback, re, string
import numpy as np
import _raveio
import _polarvolume, _polarscan
import multiprocessing
import odim_source, odc_polarQC
from Proj import dr
import datetime, dateutil.parser, pytz

import ecWxR_log
import ecWxR_trimRange
LOGGER_NAME = 'ecWxR_qc'
LOGFILE = ecWxR_log.LOGROOT + '/ecWxR_qc.log'
COMP_LOGGER_NAME = 'ecWxR_qcomp_generator'  # Same as in ecWxR_qcomp_generator
COMP_LOGFILE = ecWxR_log.LOGROOT + '/ecWxR_qcomp_generator.log'

ROOTPATH = '/fs/cetus/fs3/mrb/armp/armpdbm'
PATH = os.path.join(ROOTPATH, 'output')
DLFILE = os.path.join(PATH, 'DirectoryListing_case1_part2.txt')
#IGNORE = ['/fs/cetus/fs3/mrb/armp/armpdbm/output/2015/05/22']  # Already done
IGNORE = ['/fs/cetus/fs3/mrb/armp/armpdbm/output/2014','/fs/cetus/fs3/mrb/armp/armpdbm/output/2015']  # Already done
MAX_RAYS = 800
MAX_BINS = 2000
WAIT = 300  # Seconds to wait for the multiprocessing pool to finish, then timeout


## Copies TH to DBZH
# @param scan object
# @param boolean - whether to overwrite an existing DBZH, True=yes
def copyDBZH(scan, ow=True):
    if not scan.hasParameter('DBZH') or ow:
        if scan.hasParameter('TH'):
            if scan.hasParameter('DBZH'):
                thdata = scan.getParameter('TH').getData()
                dbzh = scan.getParameter('DBZH')
                dbzh.setData(thdata)
            else:
                cloned = scan.clone()
                dbzh = cloned.getParameter('TH')
                dbzh.quantity = 'DBZH'
                scan.addParameter(dbzh)


## Checks if DBZH parameter exists in an object, which can be either a single scan or a volume
# @param polar object, either a scan or a volume
def checkDBZH(obj, ow=True):
    if _polarvolume.isPolarVolume(obj):
        for i in range(obj.getNumberOfScans()):
            scan = obj.getScan(i)
            copyDBZH(scan, ow)
    elif _polarscan.isPolarScan(obj):
        copyDBZH(obj, ow)


## Sanity checks. If not sane, delete that sweep and carry on
def sanityChecks(pvol):
    toRemove = []
    for i in range(pvol.getNumberOfScans()):
        scan = pvol.getScan(i)
        if scan.nrays > MAX_RAYS or scan.nbins > MAX_BINS:
            toRemove.append(i)
        if "DBZH" not in scan.getParameterNames() and i not in toRemove: toRemove.append(i)
    while len(toRemove):
        i = toRemove.pop()
        pvol.removeScan(i)


## Specific to files read from Rainbow. We need to convert RHOHV to uint16 
#  and change the nodata value in order to represent values of 255=1.0. 
#  Also, check for the need to sector blank.
# @param PolarVolumeCore or PolarScanCore object
def adjustFromRB5(obj):
    if _polarvolume.isPolarVolume(obj):
        for e in range(obj.getNumberOfScans()):
            scan = obj.getScan(e)
            adjustFromRB5(scan)  # recursive call

    elif _polarscan.isPolarScan(obj):
        # First: convert RHOHV to unsigned 16-bit integer
        rhohv = obj.getParameter("RHOHV")
        data = rhohv.getData()
        data = data.astype(np.uint16)
        rhohv.setData(data)
        rhohv.nodata = 256.0

        # Second: check for sector blanking.
        txPower  = obj.getAttribute('how/TXpower')
        threshold = 0.9 * np.max(txPower)

        # Find out how many rays have tx powers beneath the threshold
        blanked = np.less(txPower, threshold)
        nrays2blank = np.sum(blanked)

        # Only continue if we know we need to, blanking all moments/quantities
        if nrays2blank:
            for pname in obj.getParameterNames():
                param = obj.getParameter(pname)
                data = param.getData()

                for ray in range(obj.nrays):
                    data[ray] = np.where(np.equal(blanked[ray], True), 
                                         param.nodata, data[ray])
                param.setData(data)


##
# Sector blanks a scan according to transmit power metadata per ray.
# If a ray has a transmit power below 90% of the maximum in the sweep,
# then it is considered sector blanked and all parameters are flagged with 
# their nodata value. Use only with data read with rb52odim?
# @param PolarScanCore object
def sectorBlank(scan):
    txPower  = scan.getAttribute('how/TXpower')
    threshold = 0.9 * np.max(txPower)

    # Find out how many rays have tx powers beneath the threshold
    blanked = np.less(txPower, threshold)
    nrays2blank = np.sum(blanked)

    # Only continue if we know we need to
    if nrays2blank:
        for pname in scan.getParameterNames():
            param = scan.getParameter(pname)
            data = param.getData()
            for ray in range(scan.nrays):
                data[ray] = np.where(np.equal(blanked[ray], True), 
                                     param.nodata, data[ray])
            param.setData(data)


## Quality controls polar volume data.
# @param string containing one ODIM_H5 file
# @param boolean True to overwrite the existing file, False to add a '_qc_' string to a new file name
# @param boolean True to trim NEXRAD data beyond the range given in ecWxR_trimRange, otherwise it won't
# @returns tuple of output file string and OK status if all is OK, or 
# input file string and traceback upon failure.
def generate(fstr, overwrite=False, trim=True):
    try:
        # Make output filename by adding qc_ prefix if we don't overwrite the original file
        if overwrite:
            ofstr = fstr
        else:
            path, filename = os.path.split(fstr)
            s = filename.split('_')
            s.insert(1, 'qc')
            filename = '_'.join(s)
            ofstr = os.path.join(path, filename)
        #if os.path.isfile(ofstr):
        #    return ofstr, "Already OK"

        #print fstr
        rio = _raveio.open(fstr)
        pvol = rio.object

        # Check that we have TH and DBZH for each scan
        # Don't trust DOPVOL-filtered DBZH. Overwrite it.
        nod = odim_source.NODfromSource(pvol)
        if nod[:2] == 'ca':
            if nod != 'cawmn':
                checkDBZH(pvol, False)  # True to overwrite, False to keep
            else:
                checkDBZH(pvol, False)
        else:
            checkDBZH(pvol, False)
        if _polarvolume.isPolarVolume(pvol):  # Don't check scans
            sanityChecks(pvol)  # Sanity checks

        # Process
        if nod[:2] == 'ca':
            if nod == 'cawmn':
                # McGill S-band - already QC:ed but how?
                algorithm_ids = ["beamb","radvol-att","radvol-broad","qi-total"]
            else:
                # RUAD C-band
                pvol.beamwidth = pvol.getAttribute('how/beamwH') * dr  # Why is this necessary?
                algorithm_ids = ["hac-filter","ropo","beamb","radvol-att","radvol-broad","qi-total"]

        else:
            # NEXRAD S-band
            if not pvol.hasAttribute('how/wavelength'): pvol.addAttribute('how/wavelength', 10.0)  # Attribute might not always be available
            algorithm_ids = ["drqc","beamb","radvol-att","radvol-broad","qi-total"]
            if trim:
                rio.object = pvol
                rio = ecWxR_trimRange.generate(ofstr, RIO=rio)  # ofstr is dummy because it doesn't exist yet
                pvol = rio.object

        odc_polarQC.algorithm_ids = algorithm_ids
        pvol.addAttribute('how/algorithm_ids', string.join(algorithm_ids, ","))

        pvol = odc_polarQC.QC(pvol)

        rio.object = pvol
        rio.save(ofstr)
        
    except Exception, e:
        return fstr, traceback.format_exc()

    return ofstr, "OK"


## Multiprocesses the generate function
# @param list of input file string lists, each list being one file string
# @returns list of two-tuples containing output file names and return status
def multi_generate(file_list, cpu_cores=None):
    if cpu_cores:
        pool = multiprocessing.Pool(cpu_cores)
    else:
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)  # Maximum-1

    results = []
    r = pool.map_async(generate, file_list, chunksize=1, callback=results.append)
    try:
        r.get(WAIT)
    except multiprocessing.TimeoutError:
        results.append(["timed out on %s" % os.path.split(file_list[0])[0]])

    pool.terminate()
    pool.join()
    del pool

    return results[0]


## Loops through input directories, creates a directory listing file containing directories only.
# @param ipath string path to root input directory
# @param ofstr string file string to contain the directory listing
def makeDirListing(ipath=PATH, ofstr=DLFILE):
    dl = []

    for yearpath in glob.glob(ipath + '/*'):
        if os.path.isdir(yearpath) and yearpath not in IGNORE:

            for monthpath in glob.glob(yearpath + '/*'):
                if os.path.isdir(monthpath) and monthpath not in IGNORE:

                    for daypath in glob.glob(monthpath + '/*'):
                        if os.path.isdir(daypath) and daypath not in IGNORE:

                            for hourpath in glob.glob(daypath + '/*'):
                                if os.path.isdir(hourpath) and hourpath not in IGNORE:

                                    for minpath in glob.glob(hourpath + '/*'):
                                        if os.path.isdir(minpath) and minpath not in IGNORE:

                                            dl.append(minpath)

    dl.sort()
    fd = open(ofstr, 'w')
    for p in dl:
        fd.write("%s\n" % p)
    fd.close()


def getDirListing(fstr=DLFILE):
    fd = open(fstr)
    LINES = fd.readlines()
    fd.close()
    lines = []
    for line in LINES:
        if line[0] != '#':
            lines.append(line[:-1])
    return lines


def selectFiles(flist, ipath):
    # Get nominal date and time for this set of files
    dt = ipath.split('/')
    year, month, day, hour, minute = dt[-5:]
    nominal = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), 0, tzinfo=pytz.UTC)

    d = {}
    for filename in flist:
        if "_qc_" not in filename:
            path, fstr = os.path.split(filename)
            if len(fstr.split('_')) == 4:  # Ignores single scans that are length 5
                node = fstr[:5]
                if node not in d.keys():
                    d[node] = filename
                else:
                    # This new file
                    ndt = fstr.split('_')[2]
                    newfiletime = dateutil.parser.parse(ndt)

                    # Existing file in dict
                    edt = d[node].split('_')[2]
                    existingfiletime = dateutil.parser.parse(edt)
                    
                    #print abs(newfiletime - nominal), abs(existingfiletime - nominal)
                    if abs(newfiletime - nominal) < abs(existingfiletime - nominal):
                        d[node] = filename

#            elif len(fstr.split('_')) == 5:  # Single scans of length 5
#                node = fstr[:5]
#                if node not in d.keys():
#                    d[node] = filename

    l = []
    for k, i in d.items():
        l.append(i)
        
    return l


# Looks for data from radars that are missing from a given bucket.
def addAdjacentFiles(files, ipath, minutes=-10, earlier=False):
    dt = ipath.split('/')
    year, month, day, hour, minute = dt[-5:]
    nominal = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), 0, tzinfo=pytz.UTC) + datetime.timedelta(minutes=minutes)

    path = string.join(dt[:8],'/') + nominal.strftime("/%Y/%m/%d/%H/%M")
    fstrs = glob.glob(path + '/*.h5')
    fstrs = selectFiles(fstrs, path, earlier)

    nodes = []
    for fstr in files:
        node = os.path.split(fstr)[1][:5]
        if node not in nodes:
            nodes.append(node)

    for fstr in fstrs:
        node = os.path.split(fstr)[1][:5]
        if node not in nodes:
            nodes.append(node)
#            print fstr
            files.append(fstr)

    return files


def generate_composite(ipath, fstrs):
    import ecWxR_tiled_composite

    splitted = ipath.split('/')
    DATE = splitted[-5] + splitted[-4] + splitted[-3]
    TIME = splitted[-2] + splitted[-1] + '00'

#    comp_filename = ecWxR_tiled_composite.multi_generate(fstrs, DATE, TIME, trim=MAXR)
    comp_filename = ecWxR_tiled_composite.multi_generate(fstrs, DATE, TIME)
    return len(fstrs), comp_filename


def main(DIR=None, multiprocess=True, logger=None, comp=True, comp_logger=None, delete=True):
    if os.path.isdir(DIR): dl = [DIR]
    else: dl = getDirListing(DIR)  # It's a file string

    for ipath in dl:
        allfiles = glob.glob(ipath + '/us*.h5') + glob.glob(ipath + '/cawmn*.h5')
        files = selectFiles(allfiles, ipath)
        files += glob.glob(ipath + '/ca*_convol_*0x3.h5')  # 0x3 is PRECIP-ET

        # Concurrent processing
        if multiprocess:
            results = multi_generate(files)
            if logger:
                logger.log(ecWxR_log.LOGLEVEL, "QCed %i of %i files in %s" % (len(results), len(files), ipath))
        else:
            # Sequential processing
            for f in files:
                ofstr, status = generate(f)
        
        # Optionally, generate a composite as long as we're in this directory
        if comp:
            qcfstrs = []
            for result in results: 
                if result[1] == 'OK': qcfstrs.append(result[0])
            nradars, comp_filename = generate_composite(ipath, qcfstrs)
            if comp_logger:
                comp_logger.log(ecWxR_log.LOGLEVEL, "%i %s" % (nradars, comp_filename))
            
        if comp and delete:
            for result in results:
                if result[1] == "OK":
                    if os.path.isfile(result[0]):
                        os.remove(result[0])
                else:
                    logger.log(ecWxR_log.LOGLEVEL, "Error QCing %s" % result[0])
    

if __name__ == "__main__":
    from optparse import OptionParser

    usage = "usage: %prog -i [<input dir> -l <make directory listing> -f [file name] -L [log file] -c [generate composite] -d [delete QC:ed files (after compositing)] -s [sequential processing]] [h]"

    parser = OptionParser(usage=usage)

    parser.add_option("-i", "--indir", dest="in_dir",
                      help="Name of input directory with files to process. If making a directory listing with -l, this path is the root to the file system.")

    parser.add_option("-l", "--directory_listing", dest="dl",
                      action="store_true",
                      help="Create a directory listing using the path given by -i as the root directory of the file system. Defaults to True.")

    parser.add_option("-f", "--directory_listing_file", dest="dlf",
                      #default=DLFILE,
                      help="If used alone, the look-up file containing input directories. Or, if combined with -l, file name to which to write the newly-generated directory listing.")

    parser.add_option("-L", "--logfile", dest="lfile",
                      default=LOGFILE,
                      help="Name of log file to write.")

    parser.add_option("-c", "--composite", dest="comp",
                      action="store_true",
                      help="Will generate composites after QC:ing.")

    parser.add_option("-d", "--delete", dest="delete",
                      action="store_true",
                      help="Will delete QC:ed files after processing. Only meaninful if combined with --composite .")

    parser.add_option("-s", "--sequential", dest="seq",
                      action="store_true",
                      help="Process data sequentially, not concurrently. Defaults to True.")
  
    (options, args) = parser.parse_args()

#    print options.in_dir, options.dl, options.dlf, options.seq
#    sys.exit()

    if options.dl:
        makeDirListing(options.in_dir, options.dlf)
    
    elif options.in_dir:
        if os.path.isdir(options.in_dir):
            if options.seq:
                main(options.in_dir, False)
            else:
                main(options.in_dir, True)
        else:
            print "Invalid input directory: %s" % options.in_dir
                
    elif options.dlf:
        if os.path.isfile(options.dlf):

            # Initialize composite logger if we're going to be compositing
            if options.comp:
                comp_logger = ecWxR_log.getLogger(COMP_LOGGER_NAME, COMP_LOGFILE)

            if options.lfile:
                logger = ecWxR_log.getLogger(LOGGER_NAME, options.lfile)
            else:
                logger = ecWxR_log.getLogger(LOGGER_NAME, LOGFILE)

            if options.seq:
                main(options.dlf, False, logger, True, comp_logger, options.delete)
            else:
                main(options.dlf, True, logger, True, comp_logger, options.delete)
        else:
            print "Invalid input file: %s" % options.dlf

    else:
        parser.print_help()
        sys.exit(-1)
