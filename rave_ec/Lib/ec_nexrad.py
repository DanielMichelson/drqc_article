'''
Copyright (C) 2015 The Crown (i.e. Her Majesty the Queen in Right of Canada)

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
#  Read NEXRAD Level II data into the BALTRAD Toolbox.
#  Data are from LDM in ar2v (compressed) format.


## 
# @file
# @author Daniel Michelson, Environment Canada
# @date 2015-11-03

# Thank you Py_ART!
import nexrad_level2

import time
from datetime import datetime, timedelta
import _rave
import _raveio
import _polarvolume
import _polarscan
import _polarscanparam
import numpy
from Proj import dr, rd
from rave_defines import UTF8
import odim_source

MSG18_LEN = 9468  # length in bytes of Message Type 18

QUANTITIES = {'REF':'TH', 'VEL':'VRADH', 'SW':'WRADH', 
              'ZDR':'ZDR', 'PHI':'PHIDP', 'RHO':'RHOHV'}
QKEYS = QUANTITIES.keys()


##
#  Quantity metadata convenience class for managing metadata associated 
#  with a given quantity/parameter.
#  @param generic Python object 
class QMeta(object):
    ## Initializer
    # @param self - this object
    # @param name - string
    # @param gain - float
    # @param offset - float
    # @param nodata - float
    # @param undetect - float
    # @param dtype - string
    def __init__(self, name, gain, offset, nodata, undetect, dtype):
        self._name = name
        self.gain = float(gain)
        self.offset = float(offset)
        self.nodata = float(nodata)
        self.undetect = float(undetect)
        self.dtype = dtype


##
#  NEXRAD Level II scales data according to F = (N-offset)/scale,
#  whereas RAVE scales data according to F = gain*N+offset.
#  This means we have to derive equivalent scaling constants.
#  Determining gain and offset is done by taking:
#  minimum discrete value : dmin
#  maximum discrete value : dmax
#  minimum continuous value : cmin
#  maximum discrete value : cmax
#  ddiff = dmax-dmin
#  gain = (cmax-cmin)/float(ddiff)
#  offset = cmin-gain
#  Note that offset is reduced by 1*gain. This shifts discrete data
#  down by one notch, enabling us to move nodata=1 to nodata=dmax
#  which follows de facto conventions elsewhere.
#  Based on RDA Build 14 (1/6/2014), coefficients in Table XVII-I scale to:
#      NAME           NAME    gain    offset    nodata  undetect dtype
QMD = {"REF"  : QMeta("REF",  0.5,    -32.5,       255, 0, 'uint8'),
       "VEL2" : QMeta("VEL2", 0.5,    -64.0,       255, 0, 'uint8'),
       "VEL1" : QMeta("VEL1", 1.0,   -128.0,       255, 0, 'uint8'),
       "SW"   : QMeta("SW",   0.5,    -64.0,       255, 0, 'uint8'),
       "ZDR"  : QMeta("ZDR",  0.0625,  -7.9375,    255, 0, 'uint8'),
       "PHI"  : QMeta("PHI",  0.352595, 0.352595, 1023, 0, 'uint16'),
       "RHO"  : QMeta("RHO",  0.003333, 0.204967,  255, 0, 'uint8')
       }


## Determines if a given file is a NEXRAD Archive file
#  @param string name of the input file
#  @returns Python boolean
def isNEXRAD(filename):
    fd = open(filename)
    s = fd.read(8)
    fd.close()
    return s[:3] == 'AR2' or s == 'ARCHIVE'


## Populates a RAVE scan object with moments/quantities/parameters from the Level II data.
#  @param l2 object containing Level II data and metadata
#  @param scan RAVE scan object to be populated
#  @param int index of the scan in the volume
def populateParams(l2, scan, index=0):
    tsi = l2.scan_info()[index]
    az = l2.get_azimuth_angles([index])
    start_az_index = numpy.argmin(az)
    ray_hdr_index = l2.scan_msgs[index][start_az_index]
    ray_hdr       = l2.msg31s[ray_hdr_index]

    for p in tsi['moments']:
        if p in QKEYS:
            param = _polarscanparam.new()
            param.quantity = QUANTITIES[p]
            #print p, param.quantity
        
            scale = ray_hdr[p]['scale']
            if p == "VEL" and scale == 1.0: qmd = QMD['VEL1']
            elif p == "VEL" and scale == 2.0: qmd = QMD['VEL2']
            else: qmd = QMD[p]
            param.gain = qmd.gain 
            param.offset = qmd.offset
            param.nodata = qmd.nodata
            param.undetect = qmd.undetect
        
            # Do our own masking, trying to separate nodata and undetect. Don't know about "range-folded" though ...
            data  = l2.get_data(p, tsi['ngates'][tsi['moments'].index(p)], scans=[index]).data  # 32-byte float
            rdata = l2.get_data(p, tsi['ngates'][tsi['moments'].index(p)], scans=[index], raw_data=True)  # 8-bit uint
            mydata = numpy.where(numpy.equal(rdata, 0), param.undetect, (data - param.offset) / param.gain).astype(qmd.dtype)
            mydata = numpy.where(numpy.equal(rdata, 1), param.nodata, mydata).astype(qmd.dtype)
        
            # Sort data according to azimuth angles, starting with the lowest angle from North, assuming clockwise ...
            if start_az_index != 0:
                begin = mydata[start_az_index:len(az)] 
                end = mydata[:start_az_index]
                mydata = numpy.concatenate((begin,end))
                
            # Quirk: REF has longer range, so we need to pad the other moments with nodata because RAVE assumes same polar geometry for all quantities
            # Also assumes that, if the scan does not contain REF, that there is no need for padding
            if "REF" in tsi['moments']:
                if p == "REF":
                    maxbins = data.shape[1]  # Assumes that REF always comes first, and that subsequent moments will relate to it 
                if data.shape[1] < maxbins:
                    dbins = maxbins-data.shape[1]
#                   padding = numpy.full((data.shape[0],dbins), qmd.nodata, qmd.dtype)  # As of numpy 1.8
                    padding = (numpy.zeros((data.shape[0],dbins)) + qmd.nodata).astype(qmd.dtype)
                    mydata = numpy.concatenate((mydata, padding), 1)
        
            param.setData(mydata)
            #print scan.elangle*rd, param.quantity, param.nrays, scan.nrays, param.nbins, scan.nbins
        
            try: scan.addParameter(param)  # This will fail where a moment has a larger value of nbins than REF
            except: pass


## Populates a RAVE scan object with everything except the moment/quantity/parameter data
#  @param l2 object containing Level II data and metadata
#  @param scan an empty RAVE scan object to be populated
#  @param int index of the scan in the volume
def populateScan(l2, scan, index=0):
    tsi = l2.scan_info()[index]
    nrays = tsi['nrays']

    # Determine starting ray
    # Assumes that azimuth angles are centred on each ray
    az = l2.get_azimuth_angles([index])
    el = l2.get_elevation_angles([index])
    start_az_index = numpy.argmin(az)

    ray_hdr_index = l2.scan_msgs[index][start_az_index]
    ray_hdr       = l2.msg31s[ray_hdr_index]
    msg31_hdr     = ray_hdr['msg31_header']
    vol_hdr       = ray_hdr['VOL']  # Stays the same for the whole volume?
    elv_hdr       = ray_hdr['ELV']  # Stays the same for the whole scan?
    rad_hdr       = ray_hdr['RAD']
    vcp_hdr       = l2.vcp['cut_parameters'][index]  # Message Type 5. Why are there more of these than nscans?

    # Get moments/quantities/parameters
    #print "SCAN %i" % index
    populateParams(l2, scan, index)

    # Now sort ray angle and time attributes
    setRayAttributes(l2, scan, index)

    # Remaining scalar attributes
    startms = l2.msg31s[l2.scan_msgs[index][0]]['msg31_header']['collect_ms']
    endms   = l2.msg31s[l2.scan_msgs[index][tsi['nrays']-1]]['msg31_header']['collect_ms']
    scan.startdate, scan.starttime = makeDateTime(l2.msg31s[l2.scan_msgs[index][0]]['msg31_header']['collect_date'], startms)
    scan.enddate, scan.endtime = makeDateTime(l2.msg31s[l2.scan_msgs[index][tsi['nrays']-1]]['msg31_header']['collect_date'], endms)

    scan.a1gate = int(start_az_index)
    scan.elangle = round(l2.get_target_angles([index])[0], 1) * dr  # Round to nearest 10th of a degree (requested?), then radians
    if "REF" in tsi['moments']:
        p = "REF"
    else: 
        p = tsi['moments'][0]
    scan.rscale = float(l2.get_range(index, p)[1] - l2.get_range(index, p)[0])  # metres
    scan.rstart = (l2.get_range(index, p)[0] - (scan.rscale/2)) * 0.001  # kilometres. Py-ART puts the location in the bin's centre.

    scan.addAttribute('how/rpm', 60/((endms-startms)/1000.0))  # Work it out, assumng start and end are same day. FIXME?

#     scan.addAttribute('how/RXbandwidth', )
#     scan.addAttribute('how/lowprf', )  # VCP header info contains only PRF Numbers, not actual frequencies
#     scan.addAttribute('how/midprf', )
#     scan.addAttribute('how/highprf', )

    if l2.atmos != None: scan.addAttribute('how/gasattn', l2.atmos.getAtmos(scan.elangle)[1])
    scan.addAttribute('how/radconstH', abs(rad_hdr['radconstH']))  # constants are negative
    scan.addAttribute('how/radconstV', abs(rad_hdr['radconstV']))
#     scan.addAttribute('how/nomTXpower', )  # Maybe found in Message Type 3
#     scan.addAttribute('how/powerdiff', )
    scan.addAttribute('how/NI', rad_hdr['nyquist_vel']*0.01)
    scan.addAttribute('how/unambig_range', rad_hdr['unambig_range']*0.1)  # Not ODIM

#     scan.addAttribute('how/Vsamples', )
    scan.addAttribute('how/scan_index', index)
    scan.addAttribute('how/scan_count', l2.nscans)

    scan.addAttribute('how/astart', 0.0)  # Could contain the calculated error

#     scan.addAttribute('how/azmethod', )
#     scan.addAttribute('how/elmethod', )
#     scan.addAttribute('how/binmethod', )

#     scan.addAttribute('how/anglesync', )
#     scan.addAttribute('how/anglesyncRes', )
    scan.addAttribute('how/malfunc', "False")
    scan.addAttribute('how/radar_msg', "")
    scan.addAttribute('how/NEZH', rad_hdr['noise_h'])
    scan.addAttribute('how/NEZV', rad_hdr['noise_v'])
#     scan.addAttribute('how/clutterType', )
#     scan.addAttribute('how/clutterMap', )

#    scan.addAttribute('how/nsampleH', rad_hdr['noise_h'])
#    scan.addAttribute('how/nsampleH', rad_hdr['noise_v'])
#     scan.addAttribute('how/SQI', )
#     scan.addAttribute('how/CSR', )
#     scan.addAttribute('how/LOG', )
    scan.addAttribute('how/VPRcorr', "False")
#     scan.addAttribute('how/peakpwr', )
#     scan.addAttribute('how/avgpwr', )
#     scan.addAttribute('how/dynrange', )
#     scan.addAttribute('how/RAC', )
    scan.addAttribute('how/BBC', "False")
#     scan.addAttribute('how/PAC', )
#     scan.addAttribute('how/S2N', )


## Reads Level II data and metadata from file and creates a corresponding RAVE object,
#  either a PVOL or a SCAN
#  @param string containing the input Level II file name
#  @param return_l2 Python Boolean for returning the Level II object or not
#  @returns If return_l2 is True, then returns Python 2-tuple containing an object representing 
#  the Level II data, and the corresponding RAVE object, otherwise returns just the RAVE object
# as the payload of a RaveIO object
def readLevelII(filename, return_l2=False):
    l2 = nexrad_level2.NEXRADLevel2File(filename)
    rio = _raveio.new()

    # Always assume we're reading volumes, not individual scans.
    if l2.nscans > 1:
        rio.object = _polarvolume.new()
    else:
        rio.object = _polarscan.new()
    obj = rio.object

    source = odim_source.SOURCE['us'+l2.volume_header['icao'][1:].lower()]
    obj.source = source.encode(UTF8)

    # Site location
    lat, lon, alt = l2.location()
    obj.longitude = lon*dr
    obj.latitude = lat*dr
    obj.height = float(alt)

    # Date and time conversions
#    obj.date, obj.time = makeDateTime(l2.volume_header['date'], l2.volume_header['time'])
    obj.date, obj.time = get_times(l2)
    
    getTopLevelHowAttrs(l2, obj)

    if rio.objectType == _rave.Rave_ObjectType_SCAN:
        populateScan(l2, obj)

    elif rio.objectType == _rave.Rave_ObjectType_PVOL:
        for i in range(l2.nscans):
            scan = _polarscan.new()
            populateScan(l2, scan, index=i)
            if len(scan.getParameterNames()) > 0:  # Don't add the scan if there are no moments in it
                obj.addScan(scan)

    if return_l2: return rio, l2
    else: return rio


# Begin helper functions

## Sets angles and timing metadata for each ray
#  @param l2 object containing Level II data and metadata
#  @param scan an empty RAVE scan object to be populated
#  @param int index of the scan in the volume
def setRayAttributes(l2, scan, index):
    startazA, stopazA, startazT, stopazT, elangles = [], [], [], [], []
    
    tsi = l2.scan_info()[index]
    nrays = tsi['nrays']
    if l2.msg18 != None:
        half_bw = getFloat(l2, 1132) / 2.
    else:
        half_bw = 0.5

    # Determine starting ray
    # Assumes that azimuth angles are centred on each ray
    az = l2.get_azimuth_angles([index])
    el = l2.get_elevation_angles([index])
    start_az_index = numpy.argmin(az)

    for i in range(nrays):
        startazA.append(az[i]-half_bw)
        stopazA.append(az[i]+half_bw)
        elangles.append(el[i]) # We only have one angle
        omjd = l2.msg31s[l2.scan_msgs[index][i]]['msg31_header']['collect_date']
        ms   = l2.msg31s[l2.scan_msgs[index][i]]['msg31_header']['collect_ms']
        esecs = makeDateTime(omjd, ms, epochs=True)
        startazT.append(esecs)  # We only have one time
        stopazT.append(esecs)

    if start_az_index > 0:  # Reshuffle
        startazA = startazA[start_az_index:] + startazA[:start_az_index] 
        stopazA  = stopazA[start_az_index:]  + stopazA[:start_az_index] 
        elangles = elangles[start_az_index:] + elangles[:start_az_index] 
        startazT = startazT[start_az_index:] + startazT[:start_az_index] 
        stopazT  = stopazT[start_az_index:]  + stopazT[:start_az_index] 

    scan.addAttribute('how/startazA', numpy.array(startazA, 'd'))
    scan.addAttribute('how/stopazA',  numpy.array(stopazA,  'd'))
    scan.addAttribute('how/elangles', numpy.array(elangles, 'd'))
    scan.addAttribute('how/startazT', numpy.array(startazT, 'd'))
    scan.addAttribute('how/stopazT',  numpy.array(stopazT,  'd'))


## Quirks for dealing with Message Type 18
# @param l2 object representing Level II data and metadata
def getMsg18(l2):
    try:
        start18 = l2._buf.index('current')
        l2.msg18 = l2._buf[start18 : start18+MSG18_LEN]
    except ValueError:
        try:
            start18 = l2._buf.index('baseline')  # If both of these fail, then the payload has no Message 18
            l2.msg18 = l2._buf[start18 : start18+MSG18_LEN]
        except ValueError:
            l2.msg18 = None


## Carrys over top-level optional metadata from Level II to RAVE
#  @param l2 object representing Level II data and metadata
#  @param obj either PVOL or SCAN
def getTopLevelHowAttrs(l2, obj):
    c = 299792458.0  # Speed of light

    vol_hdr = l2.msg31s[0]['VOL']  # Assume that this header is identical for all rays
    getMsg18(l2)
    if l2.msg18 != None: l2.atmos = ATMOS(l2)
    else: l2.atmos = None

    tsi = l2.scan_info()[l2.nscans-1]  # Highest tilt contains all moments
    msg5_hdr = l2.vcp['msg5_header']
    
    obj.addAttribute('how/task', "VCP %i" % l2.vcp['msg5_header']['pattern_number'])  # Top level
    obj.addAttribute('how/system', "NEXRAD RDA/RPG")
    obj.addAttribute('how/TXtype', "klystron")
    if "RHO" in tsi["moments"]: 
        obj.addAttribute('how/poltype', "simultaneous-dual")
        obj.addAttribute('how/polmode', "simultaneous-dual")
    else: 
        obj.addAttribute('how/poltype', "single")
        obj.addAttribute('how/polmode', "single-H")

    obj.addAttribute('how/software', "NEXRAD RDA")
    obj.addAttribute('how/sw_version', "14.0")

    obj.addAttribute('how/simulated', 'False')

    if l2.msg18 != None:
        tx_mhz = getInt(l2, 1092)
        obj.addAttribute('how/wavelength', c / (tx_mhz * 1000000.0) * 100)  # cm
        bw = getFloat(l2, 1132)
        bw = 1.0 if round(bw,2) == 0.0 else bw
        obj.beamwidth = bw * dr
        obj.addAttribute('how/pulsewidth', float(msg5_hdr['pulse_width']))  # Short=2, Long=4. Need scaling?
        obj.addAttribute('how/antgainH', getFloat(l2, 1136))  # Only single antenna gain
        obj.addAttribute('how/antgainV', getFloat(l2, 1136))
        obj.addAttribute('how/beamwH', bw)  # Only single beamwidth
        obj.addAttribute('how/beamwV', bw)
        obj.addAttribute('how/phasediff', getFloat(l2, 1112))  # ODIM doesn't ask for 'normalized' initial differential phase? If so, then the index should be 1116.
        obj.addAttribute('how/zcalH', getFloat(l2, 8880))  # These could be incorrectly read
        obj.addAttribute('how/zcalV', getFloat(l2, 8884))

        losses = PATH_LOSSES(l2)
        #obj.addAttribute('how/TXlossH', losses.TXloss)  # No separation between polarizations
        #obj.addAttribute('how/TXlossV', losses.TXloss)
        #     obj.addAttribute('how/injectlossH', )
        #     obj.addAttribute('how/injectlossV', )
        #obj.addAttribute('how/RXlossH', losses.RXloss)
        #obj.addAttribute('how/RXlossV', losses.RXloss)
    else:
        obj.beamwidth = 1.0 * dr

    obj.addAttribute('how/radomelossH', 0.0)  # Are included in the PATH_LOSSES array
    obj.addAttribute('how/radomelossV', 0.0)
    obj.addAttribute('how/nomTXpower', vol_hdr['power_h'])  # This is probably not right, but the closest we can get without reading Message Type 3    
    obj.addAttribute('how/zdr_offset', vol_hdr['diff_refl_calib'])  # Not ODIM (yet)


##
#  PATH_LOSSES array in Table XV
class PATH_LOSSES(object):
    ## Initializer
    # @param self - this object
    # @param l2 - Level II data and metadata object
    def __init__(self, l2):
        if l2.msg18 != None:
            self.path_7  = getFloat(l2, 668)  # Vertical
            self.path_13 = getFloat(l2, 692)
            self.path_28 = getFloat(l2, 752)  # Horizontal
            self.path_30 = getFloat(l2, 760)
            self.path_31 = getFloat(l2, 764)
            self.path_32 = getFloat(l2, 768)
            self.path_33 = getFloat(l2, 772)
            self.path_34 = getFloat(l2, 776)
            self.path_35 = getFloat(l2, 780)
            self.path_37 = getFloat(l2, 784)
            self.path_38 = getFloat(l2, 792)
            self.path_39 = getFloat(l2, 796)
            self.path_40 = getFloat(l2, 800)
            self.path_41 = getFloat(l2, 804)
            self.path_42 = getFloat(l2, 808)
            self.path_43 = getFloat(l2, 812)
            self.path_44 = getFloat(l2, 816)
            self.path_45 = getFloat(l2, 820)
            self.path_46 = getFloat(l2, 824)
            self.path_47 = getFloat(l2, 828)
            self.path_48 = getFloat(l2, 832)
            self.path_49 = getFloat(l2, 836)
            self.path_50 = getFloat(l2, 840)
            self.path_52 = getFloat(l2, 848)
            self.path_53 = getFloat(l2, 852)
            self.path_58 = getFloat(l2, 872)
            self.path_59 = getFloat(l2, 876)
            self.path_60 = getFloat(l2, 880)
            self.path_61 = getFloat(l2, 884)
            self.path_63 = getFloat(l2, 892)
            self.path_64 = getFloat(l2, 896)
            self.path_65 = getFloat(l2, 900)
            self.path_66 = getFloat(l2, 904)
            self.path_67 = getFloat(l2, 908)
            self.path_68 = getFloat(l2, 912)
            self.caldiff = getFloat(l2, 920)  # Noncontrolling channel calibration difference

            # After discussions with Vlado and Norman, this is our best guess. Probably too speculative.
            self.TXloss = self.path_13 + self.path_33 + self.path_34 + self.path_37 + self.path_38 + self.path_39 + self.path_40 + self.path_41 + self.path_43 + self.path_50
            self.RXloss = self.path_7  + self.path_28 + self.path_35 + self.path_58 + self.path_59 + self.path_60 + self.path_61 + self.path_63 + self.path_64 + self.path_65 + self.path_66 + self.path_68


##
#  Two-way atmospheric loss as a function of elevation angle, also Table XV
class ATMOS(object):
    def __init__(self, l2):
        ## Initializer
        # @param self - this object
        # @param l2 - Level II data and metadata object
        if l2.msg18 != None:
            self.atmos_0  = {"min":-1.0, "max":-0.5, "atmos":getFloat(l2,  992)}
            self.atmos_1  = {"min":-0.5, "max": 0.0, "atmos":getFloat(l2,  996)}
            self.atmos_2  = {"min": 0.0, "max": 0.5, "atmos":getFloat(l2, 1000)}
            self.atmos_3  = {"min": 0.5, "max": 1.0, "atmos":getFloat(l2, 1004)}
            self.atmos_4  = {"min": 1.0, "max": 1.5, "atmos":getFloat(l2, 1008)}
            self.atmos_5  = {"min": 1.5, "max": 2.0, "atmos":getFloat(l2, 1012)}
            self.atmos_6  = {"min": 2.0, "max": 2.5, "atmos":getFloat(l2, 1016)}
            self.atmos_7  = {"min": 2.5, "max": 3.0, "atmos":getFloat(l2, 1020)}
            self.atmos_8  = {"min": 3.0, "max": 3.5, "atmos":getFloat(l2, 1024)}
            self.atmos_9  = {"min": 3.5, "max": 4.0, "atmos":getFloat(l2, 1028)}
            self.atmos_10 = {"min": 4.0, "max": 4.5, "atmos":getFloat(l2, 1032)}
            self.atmos_11 = {"min": 4.5, "max": 5.0, "atmos":getFloat(l2, 1036)}
            self.atmos_12 = {"min": 5.0, "max":90.0, "atmos":getFloat(l2, 1040)}
            
    ## Looks up atmospheric loss for a given elevation angle
    # @param self - this object
    # @param float elangle in radians
    # @returns Python 2-tuple (string, float) containing the attribute name containing the loss, 
    # ie. self.atmos_n, and the loss itself in dB.
    def getAtmos(self, elangle):
        el = elangle * rd
        for k,i in self.__dict__.items():
            if (i['min'] <= el < i['max']):
                return k, i['atmos']
            

## Convenience function, access a float scalar in Message Type 18
#  @param l2 - Level II data and metadata object
#  @param index - int index of the float in Message Type 18
#  @ returns float 
def getFloat(l2, index):
    return numpy.fromstring(l2.msg18[index:index+4], numpy.float32).byteswap().astype('d')[0]


## Convenience function, access an int scalar in Message Type 18
#  @param l2 - Level II data and metadata object
#  @param index - int index of the int in Message Type 18
#  @ returns int 
def getInt(l2, index):
    return numpy.fromstring(l2.msg18[index:index+4], numpy.int32).byteswap().astype('i')[0]


def timesFromDaysSeconds(days, secs):
    offset = timedelta(days=int(days[0]) - 1, seconds=int(secs[0]))
    time_start = datetime(1970, 1, 1) + offset
    seconds = secs - int(secs[0]) + (days - days[0]) * 86400
    return time_start, seconds
    

## Retrieve the times at which the rays were collected. Shoutout: Py-ART!
# @param l2 nexrad_level2.NEXRADLevel2File object
# @param scans boolean, scans to use, default=None
# @returns two-tuple containing Datetime, initial start date and time, and 
# float64 array containing Offset in seconds from the initial time at which the rays
# in the requested scans were collected.
def get_times(l2, scans=None, pa=False):
    if scans is None:
        scans = range(l2.nscans)
    days = l2._msg31_array(scans, 'collect_date')
    secs = l2._msg31_array(scans, 'collect_ms') / 1000.
    offset = timedelta(days=int(days[0]) - 1, seconds=int(secs[0]))
    time_start, seconds = timesFromDaysSeconds(days, secs)
#    time_start = datetime(1970, 1, 1) + offset
#    seconds = secs - int(secs[0]) + (days - days[0]) * 86400
    if pa:
        return time_start, seconds
    else:
        return time_start.strftime("%Y%m%d"), time_start.strftime("%H%M%S")


## Creates a date and time formatted for /what/date and /what/time
#  @param omjd - int offset modified Julian Day
#  @param ms - int milliseconds past midnight
#  @param epochs - Python boolean, whether to return day seconds or not
#  @returns If epochs=True, returns day seconds as a float, else returns a 2-tuple 
#  containing (YYYYmmdd, HHMMSS) as strings 
def makeDateTime(omjd, ms, epochs=False):    
    JDconstant = 2440586.5  # Modifled Julian date constant, only for NEXRAD?
    MJD = int(round(omjd+JDconstant, 0))
    Date = str(julday2date(MJD))
    tt = time.strptime(Date, "%Y%m%d")
    day_seconds = time.mktime(tt)
    day_seconds += ms * 0.001  # Miliseconds to seconds
    if epochs == True: return day_seconds
    tt = time.gmtime(day_seconds)
    Time = time.strftime("%H%M%S", tt)
    return Date, Time


## Converts Modified Julian day to integer. Thanks Iwan!
#  julian should be rounded to the nearest integer
#  @param julian int - rounded Julian Day
#  @returns YYYYmmdd as an int
def julday2date(julian):
    IGREG = 2299161
    if julian >= IGREG:
        jalpha = int((julian-1867216-0.25)/36524.25)
        ja=julian+1+jalpha-int(0.25*jalpha)
    else: ja=julian
    jb=ja+1524
    jc=int(6680.0+((jb-2439870)-122.1)/365.25)
    jd=int(365*jc+(0.25*jc))
    je=int((jb-jd)/30.6001)
    dd=jb-jd-30.6001*je
    if dd < 1.0: dd+=1  # The 1+ is fishy, but we'll take it
    mm=je-1
    if mm > 12: mm -= 12
    yyyy=jc-4715
    if mm > 2: yyyy=yyyy-1
    if yyyy <= 0: yyyy=yyyy-1
    return int(round(dd+100*(mm+100*yyyy),0))


def pruneScans(rio, atleast=4):
    pvol = rio.object
    indices = []
    for i in range(pvol.getNumberOfScans()):
        scan = pvol.getScan(i)
        pnames = scan.getParameterNames()
        if len(pnames) < atleast:
            indices.append(i)

    indices.reverse()
    for i in indices:
        pvol.removeScan(i)

    rio.object = pvol
    return rio


# End helper functions


if __name__=="__main__":
    print julday2date(2457328)  # 2015-11-01
