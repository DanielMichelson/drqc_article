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
##
#  McGill format reader
#  McGill indices are base 1, except the bin_number!


## 
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-01-22

import time
import _rave, _raveio
import _polarvolume, _polarscan, _polarscanparam
from Proj import dr
from numpy import *

HEADER_LENGTH = 4096
RECORD_LENGTH = 2048
SEGMENT_LENGTH = 19
SEGMENTS = 107
NRAYS = 360
SCANT = 10  # Time in seconds to acquire a sweep.
QUANTITIES = {1 : "DBZH", 4 : "VRADH", 16 : "ZDR", 17 : "PHIDP",
              18 : "RHOHV", 19 : "KDP"}  # Only 1 and 4 are available

# esteps are the times in seconds between tilts in the ascending scan strategy
# These are real times from an acquisition in April 2012. They are used to 
# adjust the timing metadata backwards, as McGill timestamps the end of data 
# acquisition. They are indicative only, but the best we can do.
esteps = (0.921875, 0.914062, 0.914062, 1.04688, 0.976562, 1.00000, 0.984375, 
          1.02344, 1.47656, 1.33594, 1.17188, 1.71094, 2.17188, 2.82812, 
          3.12500, 3.32031, 3.71875, 3.92969, 4.44531, 4.83594, 5.13281, 
          5.22656, 5.29688, 0.0)  # Last value is a dummy


## Empty generic container, to be populated
# @param object
class McGill(object):
    def __init__(self):
        pass


## Is this a McGill file?
# @param string containing the input file name
# @returns True if the file is a McGill file, otherwise False
def isMcGill(filename):
    fd = open(filename)
    s = fd.read(6)
    fd.close()
    return s == "mcgill"



## Reads the contents of a McGill file, according to
# http://deneb.tor.ec.gc.ca/urpdoc/reference/science/mcgill_volume_scan.html
# Attribute naming follows this document.
# The generic container is used to represent the contents of the file as:
# mobj : top-level McGill() object
# mobj.logical_records : a list of McGill objects containing one logical record each
# mobj.logical_records[index].segments : a list of 107 McGill objects, each 
# representing a segment
# @param string input file name
# @returns McGill object representing the file contents
def readMcGill(filename):
    mobj = McGill()
    fd = open(filename)

    # Start reading header
    fd.seek(46*2)
    #mobj.dum0 = fd.read(46*2)
    mobj.number_Logical_Records = int(fromstring(fd.read(2), int16))
    fd.seek(3*2, 1)
    #mobj.dum1 = fd.read(3*2)
    mobj.Volume_Scan_Format = int(fromstring(fd.read(2), int16))
    fd.seek(5*2, 1)
    #mobj.dum2 = fd.read(2*5)
    mobj.hours = int(fromstring(fd.read(4), int32))
    mobj.minutes = int(fromstring(fd.read(4), int32))
    mobj.seconds = int(fromstring(fd.read(4), int32))
    mobj.day = int(fromstring(fd.read(4), int32))
    mobj.month = int(fromstring(fd.read(4), int32))
    mobj.year = int(fromstring(fd.read(4), int32))
    mobj.radar_Id = int(fromstring(fd.read(4), int32))
    mobj.radar_latitude = float(fromstring(fd.read(4), float32))
    mobj.radar_longitude = float(fromstring(fd.read(4), float32))
    mobj.number_elevations = int(fromstring(fd.read(4), int32))
    mobj.elevation_angles = []
    for i in range(mobj.number_elevations):
        mobj.elevation_angles.append(float(fromstring(fd.read(4), float32)))
    mobj.azimuth_offset = int(fromstring(fd.read(2), int16))
    mobj.viraq_flag = fd.read(2)
    mobj.clutter_filter = fd.read(2)
    fd.seek(315*2, 1)
    #mobj.dum3 = fd.read(315*2)
    mobj.met_param = int(fromstring(fd.read(2), int16))
    fd.seek(2 ,1)
    #mobj.dum4 = fd.read(2)
    mobj.value_offset = float(fromstring(fd.read(4), float32))
    mobj.cal_slope = float(fromstring(fd.read(4), float32))
    mobj.antenna_programme = int(fromstring(fd.read(2), int16))
    fd.seek(4, 1)
    #mobj.dum5 = fd.read(2)
    #mobj.dum6 = fd.read(2)
    mobj.cscan_format = int(fromstring(fd.read(2), int16))
    mobj.range_unfolded = int(fromstring(fd.read(2), int16))
    mobj.vad_velocity_unfolded = int(fromstring(fd.read(2), int16))
    mobj.numb_vad_unf_pts = []
    for i in range(mobj.number_elevations):
        mobj.numb_vad_unf_pts.append(int(fromstring(fd.read(2), int16)))
    mobj.numb_range_unf_pts = []
    for i in range(mobj.number_elevations):
        mobj.numb_range_unf_pts.append(int(fromstring(fd.read(2), int16)))
    mobj.range_bins_array_size = int(fromstring(fd.read(2), int16))
    fd.seek(2, 1)
    #mobj.dum7 = fd.read(2)
    mobj.shift_cscan_flag = int(fromstring(fd.read(2), int16))
    mobj.shift_speed = int(fromstring(fd.read(2), int16))
    mobj.shift_dir = int(fromstring(fd.read(2), int16))
    fd.seek(48*4, 1)
    #mobj.dum8 = fd.read(24*4)
    #mobj.dum9 = fd.read(24*4)
    mobj.vert_grad_unfolded = int(fromstring(fd.read(2), int16))
    mobj.numb_vert_grad_unf_pts = []
    for i in range(mobj.number_elevations):
        mobj.numb_vert_grad_unf_pts.append(int(fromstring(fd.read(2), int16)))
    fd.seek(12, 1)
    #mobj.dum10 = fd.read(4)  # documentation says 2 bytes, but it's 4
    #mobj.dum11 = fd.read(4)
    #mobj.dum12 = fd.read(4)
    mobj.radial_grad_unfolded = int(fromstring(fd.read(2), int16))
    mobj.numb_radial_grad_unf_pts = []
    for i in range(mobj.number_elevations):
        mobj.numb_radial_grad_unf_pts.append(int(fromstring(fd.read(2), int16)))
    mobj.prf1 = []
    for i in range(mobj.number_elevations):
        mobj.prf1.append(int(fromstring(fd.read(2), int16)))
    mobj.prf2 = []
    for i in range(mobj.number_elevations):
        mobj.prf2.append(int(fromstring(fd.read(2), int16)))
    mobj.nyq_range = []
    for i in range(mobj.number_elevations):
        mobj.nyq_range.append(int(fromstring(fd.read(2), int16)))
    mobj.max_range = []
    for i in range(mobj.number_elevations):
        mobj.max_range.append(int(fromstring(fd.read(2), int16)))
    mobj.nyq_vel = []
    for i in range(mobj.number_elevations):
        mobj.nyq_vel.append(float(fromstring(fd.read(4), float32)))
    mobj.max_vel = []
    for i in range(mobj.number_elevations):
        mobj.max_vel.append(float(fromstring(fd.read(4), float32)))
    mobj.usable_elv = []
    for i in range(mobj.number_elevations):
        mobj.usable_elv.append(int(fromstring(fd.read(1), uint8)))
    mobj.prev_sub_area_speed, mobj.prev_sub_area_dir = [], []
    for i in range(9):
        mobj.prev_sub_area_speed.append(int(fromstring(fd.read(2), int16)))
    for i in range(9):
        mobj.prev_sub_area_dir.append(int(fromstring(fd.read(2), int16)))
    #mobj.dum_pad = fd.read(1166*2)

    # Start reading data, by logical record
    mobj.logical_records = []

    fd.seek(HEADER_LENGTH)
    last_record = 0
    while last_record == 0:
        lr = McGill()
        record = fd.read(RECORD_LENGTH)
        lr.high = int(fromstring(record[0], uint8))
        lr.low = int(fromstring(record[1], uint8))
        lr.logical_record_number = 64 * lr.high + lr.low
        last_record = int(fromstring(record[2], uint8))
        lr.beginning_elevation_number = int(fromstring(record[3], uint8))
        lr.end_elevation_number = int(fromstring(record[4], uint8))
        lr.segstr = record[14:2047]
        lr.segments = []

        # Read SEGMENTS, each SEGMENT_LENGTH bytes long.
        segpos = 0
        for i in range(SEGMENTS):
            seg = McGill()
            this_seg = lr.segstr[segpos:segpos+SEGMENT_LENGTH]
            seg.N = int(fromstring(this_seg[0], uint8))

            # Data segment
            if 1 <= seg.N <= 30:
                seg.type = "data"
                seg.high = int(fromstring(this_seg[1], uint8))
                seg.low = int(fromstring(this_seg[2], uint8))
                seg.bin_number = 16 * (seg.N - 1)# + 1
                seg.radial_number = 64 * seg.high + seg.low
                seg.data = fromstring(this_seg[3:], uint8)

            # Elevation segment
            elif 31 <= seg.N <= 55:
                seg.type = "elevation"
                seg.elevation_number = seg.N - 31
                seg.elevation_angle = mobj.elevation_angles[seg.elevation_number-1]

            # End-of-data segment can be ignored
            elif seg.N == 63:
                seg.type = "eod"

            # For some reason, there are segments of type 0, which are 
            # undocumented. Ignore these.
            if seg.N > 0:
                lr.segments.append(seg)
            segpos += SEGMENT_LENGTH

        mobj.logical_records.append(lr)

    fd.close()
    return mobj


## Takes the output of readMcGill and creates contiguous scans of data.
# This is done by pasting the contents of each McGill segment into the 
# equivalent position in the corresponding contiguous scan.
# @param McGill object representing file contents
def makeScans(mobj):
    mobj.scans = []

    # Create empty arrays for each scan
    for i in range(mobj.number_elevations):
        mobj.scans.append(zeros((NRAYS, 120+(60*2)+(60*4)), uint8))

    # Populate them
    for lr in mobj.logical_records:
        for seg in lr.segments:

            # Elevation segment types always preceed data types
            if seg.type == "elevation":
                scan = seg.elevation_number -1

            elif seg.type == "data":
                ray = seg.radial_number - 1

                # Bins 112-119 are 1 km, 120-128 are 2 km, 112-135 km
                if seg.bin_number == 112:
                    part1 = seg.data[:8]
                    part2 = repeat(seg.data[8:], 2)
                    data = concatenate([part1, part2])
                    frombin = 112

                # All 2 km, 136-231 km
                elif 128 <= seg.bin_number < 176:
                    data = repeat(seg.data, 2)
                    diff = (seg.bin_number - 128) / 16.0
                    frombin = 136 + 32 * diff  # 16 and 32 combo makes no sense?

                # Bins 176-179 are 2 km, 180-239 are 4 km, 232-287 km
                elif seg.bin_number == 176:
                    part1 = repeat(seg.data[:4], 2)
                    part2 = repeat(seg.data[4:], 4)
                    data = concatenate([part1, part2])
                    frombin = 232

                # All 4 km, 288- km
                elif 192 <= seg.bin_number:
                    data = repeat(seg.data, 4)
                    diff = (seg.bin_number - 192) / 32.0
                    frombin = 288 + 64 * diff  # 32 and 64 combo makes no sense?

                # All 1 km, 0-111 km
                else:
                    data = seg.data
                    frombin = seg.bin_number

                tobin = int(frombin) + len(data)

                mobj.scans[scan][ray][frombin:tobin] = data


## McGill data times are the end of data acquisition. This function guestimates
# the beginning dates and times of each scan in the volume.
# @param McGill object representing file contents
def adjustTimes(mobj):
    startdate, starttime, enddate, endtime = [], [], [], []
    
    tt = (mobj.year, mobj.month, mobj.day, 
          mobj.hours, mobj.minutes, mobj.seconds, 0, 0, 0)
    epochs = time.mktime(tt) - (sum(esteps) + SCANT*mobj.number_elevations)

    for i in range(mobj.number_elevations):
        start  = time.gmtime(epochs)
        startdate.append(time.strftime("%Y%m%d", start))
        starttime.append(time.strftime("%H%M%S", start))
        epochs += SCANT
        end = time.gmtime(epochs)
        enddate.append(time.strftime("%Y%m%d", end))
        endtime.append(time.strftime("%H%M%S", end))
        epochs += esteps[i]

    mobj.startdate = startdate
    mobj.starttime = starttime
    mobj.enddate = enddate
    mobj.endtime = endtime


## Creates a PVOL from the McGill object
# @param McGill object representing file contents
# @returns BALTRAD/ODIM PVOL object
def makePVOL(mobj):
    pvol = _polarvolume.new()

    pvol.source = "NOD:cawmn,PLC:McGill QC"
    pvol.longitude = mobj.radar_longitude * dr
    pvol.latitude = mobj.radar_latitude * dr
    pvol.height = 76.0          # From a URP Site.conf file
    pvol.beamwidth = 0.85 * dr  # From a URP Site.conf file
    pvol.date = mobj.startdate[0]
    pvol.time = mobj.starttime[0]
    pvol.addAttribute("how/simulated", "False")
    pvol.addAttribute("how/system", "McGill")
    pvol.addAttribute("how/TXtype", "klystron")
    pvol.addAttribute("how/polmode", "simultaneous-dual")
    pvol.addAttribute("how/wavelength", 10.4)  # According to the McGill spec
    pvol.addAttribute("how/rpm", 6.0)          # According to the McGill spec

    for i in range(mobj.number_elevations):
        scan = _polarscan.new()
        scan.elangle = mobj.elevation_angles[i] * dr
        scan.rscale = 1000.0
        scan.rstart = 0.25          # According to URP decoder
        scan.a1gate = 0             # Unknown
        scan.startdate = mobj.startdate[i]
        scan.starttime = mobj.starttime[i]
        scan.enddate = mobj.enddate[i]
        scan.endtime = mobj.endtime[i]
        scan.addAttribute("how/astart", 0.5)   # According to the McGill spec
        scan.addAttribute("how/lowprf", mobj.prf1[i])  # PRFs are identical
        #scan.addAttribute("how/midprf", )
        scan.addAttribute("how/highprf", mobj.prf2[i])

        param = _polarscanparam.new()
        param.quantity = QUANTITIES[mobj.met_param]  # Only DBZH and VRADH
        param.nodata = 255.0        # Unknown
        param.undetect = 0.0        # Implied
        param.gain = mobj.cal_slope
        param.offset = mobj.value_offset
        param.setData(mobj.scans[i])

        scan.addParameter(param)
        pvol.addScan(scan)

    return pvol
        

## Each PVOL contains only one moment, so merge several of these into one.
# Assume the first PVOL contains DBZH and the second VRADH.
# @param list of (two) PVOLs
# @returns PVOL object containing (both) moments per scan.
def mergePVOLs(pvols):
    refl, wind = pvols
    for i in range(wind.getNumberOfScans()):
        zscan, vscan = refl.getScan(i), wind.getScan(i)
        vradh = vscan.getParameter("VRADH")
        zscan.addParameter(vradh)
    return refl


## Reads McGill data from file and returns a BALTRAD/ODIM PVOL object for a 
# single moment
# @param string of McGill file
# @returns PVOL object containing one moment for each scan.
def file2pvol(filename):
    mobj = readMcGill(filename)
    makeScans(mobj)
    adjustTimes(mobj)
    return makePVOL(mobj)


## Reads McGill data from two files into a single BALTRAD/ODIM PVOL
# @param string of the McGill file containing reflectivity (DBZH)
# @param string of the McGill file containing radial wind velocity (VRADH)
# @returns PVOL object containing both moments per scan
def read(zfile, vfile):
    refl = file2pvol(zfile)
    wind = file2pvol(vfile)
    return mergePVOLs([refl, wind])


if __name__=="__main__":
    pass
