#!/usr/bin/python
'''extract point data from odimH5 files,
   script called with extract_point_data.sh to enable BALTRAD
   assumes that odimH5 files in ./dir_store/YYYYMMDDHHMM (see config.py)
   in main:
    extract_point_values() reduces H5 files to binary numpy "npz" files
    expand_for_EMET() reformats npz files to txt inputable to EMET
  the text EMET files are used by verify_with_emet.sh



'''

from datetime import datetime
import csv
import multiprocessing
import numpy
import os
import sys
import time
import cPickle as pickle

import load_metadata
from config import dir_store


# BALTRAD tools
import Proj
import _iris2odim
import _polarscan
import _polarvolume
import _rave
import _raveio
from _rave import RaveValueType_UNDEFINED as UNDEFINED  # -1
from _rave import RaveValueType_UNDETECT  as UNDETECT   # 0
from _rave import RaveValueType_NODATA    as NODATA     # 1
from _rave import RaveValueType_DATA      as DATA       # 2

from pprint import pprint, pformat
from pdb import set_trace


# D/s for holding compressed EMET point data
dtype_radar4verif = [
        ('datetime', 'datetime64[s]'),    # NaT units to 1-second precision
        ('id_radarSTN', '<U9'),
        ('distance', '<i2'),
        ('height', '<i2'),
        ('TH', [('f0', 'i1'), ('f1', '<f2')]),    # '<f2' restricts range, -99999.0 -> BUG
        ('DBZH', [('f0', 'i1'), ('f1', '<f2')]),
    ]


D_stn = load_metadata.load_station()
D_radar = load_metadata.load_radar()
D_radar_station = load_metadata.load_radar_station()

# radar data for 2016 07 and 08
dir_npz = dir_store+'/npz'
dir_emet = dir_store+'/emet'


def worker_extract_point_values(input):
    ''' extract all point data for one time bucket
    '''
    ymdhm = input
    tm_sought = datetime.strptime(ymdhm, '%Y%m%d%H%M')
    D_all = {}   # collect everything in a dict, pack to npz at end
    dir_input = dir_store+'/'+ymdhm
    fnames = os.listdir(dir_input)
    for fname in fnames:
      # try:
        filePath = dir_input+'/'+fname
        rio = _rave.open(filePath)    # use ODIM h5 functionality
        obj = rio.object
        if not _polarvolume.isPolarVolume(obj):
            sys.stderr.write('Warning_NP : no PolarVolume in %s\n' % filePath)
            continue
        tm_radar = datetime.strptime(obj.date+obj.time, '%Y%m%d%H%M%S')
        diff = tm_radar - tm_sought
        diff_minutes = abs(diff.days * 1440 + diff.seconds / 60)
        if diff_minutes >= 10:    # ignore if not near whole hour
            continue
        dt_64 = numpy.datetime64('%4d-%02d-%02dT%02d:%02d:%02d+0000' % (
                tm_radar.year, tm_radar.month, tm_radar.day,
                tm_radar.hour, tm_radar.minute, tm_radar.second))
        id_radar = obj.source.split('NOD:')[1].split(',PLC:')[0]
        if id_radar not in D_radar_station:  # e.g., Guam was QC'ed but innored for verification
            continue
        # PS id_radar could also be gotten from fname[:5] now

        # TODO confirm second arg correct, that 0.0, 0 gets nearest to horizon (0.0)
        # even though usbyx Key West 14 scans range 0.5 - 6.4 deg
        scan = obj.getScanClosestToElevation(0.0, 0)
        if scan is None:    # true for 3 radar h5 files in 201608
            sys.stderr.write('Warning: obj.getScanClosestToElevation(0.0, 0) = None for %s\n' %
                filePath)
            continue

        D_all[id_radar] = {}
        heightField = scan.getHeightField()
        stns = D_radar_station[id_radar]    # stations to match with radar
        for id_stn in stns:
            d_stn = D_stn[id_stn]
            lonlat = d_stn['lonlat']
            nearestIndex = scan.getNearestIndex(lonlat)
            if nearestIndex is None:    # showstopper for this radar-stn pair
                obj_foo = _polarscan.new()
                obj_foo.longitude, obj_foo.latitude = obj.longitude, obj.latitude
                distance = obj_foo.getDistance(lonlat)
                if distance > 1950.:   # else too close, e.g., uscrp KCRP dist 1912.58
                    sys.stderr.write('Warning_nIN : nearestIndex None, %s %s, dist = %.2f\n' % (
                            id_radar, id_stn, distance))
                continue
            else:
                distance = scan.getDistance(lonlat)
                height = heightField.getValue(int((distance + 0.5)/scan.rscale), 0)
                if height[0] == 0:
                    sys.stderr.write('Warning_HGT: undefined for %s %s dist = %.1f\n' % (    # was not thrown
                        id_radar, id_stn, distance))
                    continue    # try another station
                d_radar_stn = D_all[id_radar][id_stn] = {}
                d_radar_stn['dt_64'] = dt_64
                d_radar_stn['height'] = int(height[1] + 0.5)
                d_radar_stn['distance'] = int(distance / 1000) # m to km
                parameterNames = scan.getParameterNames()

                for parameter in parameterNames:    # see everything that's available
                    scan.defaultparameter = parameter
                    # value = scan.getConvertedValue(nearestIndex[0], nearestIndex[1])
                    d_radar_stn[parameter] = scan.getConvertedValue(nearestIndex[0], nearestIndex[1])

      # except:
      #   sys.stderr.write('Warning: could not extract from %s\n' % fname)

    # pprint(D_all) ; sys.exit()    # XXX

    num_rows = 0
    for id_radar in D_all.keys():
        d_radar = D_all[id_radar]
        for id_stn in d_radar.keys():
            d_rs = d_radar[id_stn]
            if len(d_rs) == 0:        # empty radarStation dict slipped though
                del d_radar[id_stn]   # remove before saving to array
        num_rows += len(d_radar)

    # convert dictionary of radar-station info to numpy array
    arr = numpy.zeros(num_rows, dtype=dtype_radar4verif)
    n = 0
    for id_radar in sorted(D_all):
        d_radar = D_all[id_radar]
        for id_stn in sorted(d_radar):
            rs = d_radar[id_stn]    # a radar-station pair
            a = arr[n]
            a['datetime'] = rs['dt_64']
            a['id_radarSTN'] = id_radar+id_stn
            a['distance'] = rs['distance']
            a['height'] = rs['height']
            for parameter in ['TH', 'DBZH']:
                if parameter in rs:
                    a[parameter] = rs[parameter]
                else:
                    a[parameter] = (NODATA, -999.0)
            n += 1

    fname_output = '%s/%s.npz' % (dir_npz, ymdhm)
    numpy.savez_compressed(fname_output, array1=arr)
    sys.stdout.write('saved %s\n' % fname_output)


def extract_point_values():
    ''' from each time's set of h5 files, make .npz files
    '''
    tm_0 = time.time()
    L_ymdhm = sorted([x for x in os.listdir(dir_store) if x[:3] == '201'])
    inputs = L_ymdhm
    # inputs = L_ymdhm[0:1] # XXX
    if sequential:
        outputs = []
        for input in inputs:
            outputs.append(worker_extract_point_values(input))
    else:
        pool = multiprocessing.Pool()    
        outputs = pool.map(worker_extract_point_values, inputs)
        pool.close()
        pool.join()

    num_expts = len(inputs)
    tm_1 = time.time()
    print 'secs/expt: %.2f  (%.1f / %d)' % ((tm_1-tm_0) / num_expts, tm_1-tm_0, num_expts)


def translate_DBZ_BALTRAD_to_EMET(x):
    """translate BALTRAD bin 2-tuple value to usable with EMET
    """
    if x['f0'] == UNDETECT:
        value = '-99'    # what would make sense here ??? not 0.0
    elif x['f0'] == DATA:
        value = '%.1f' % x['f1']
    elif x['f0'] == NODATA:
         value = '-999'
    else:
        sys.stderr.write('Error : translate_DBZ_BALTRAD_to_EMET(%s)\n' % str(x))
        sys.exit(1)
    return value


def round_to_hour(dt):
    """convert precise radar time to nearest whole hour, only time usable by EMET
    """
    from datetime import timedelta
    dt_start_of_hour = dt.replace(minute=0, second=0, microsecond=0)
    dt_half_hour = dt.replace(minute=30, second=0, microsecond=0)
    if dt < dt_half_hour:
        dt = dt_start_of_hour                         # round down
    else:
        dt = dt_start_of_hour + timedelta(hours=1)    # round up
    return dt


header='date_orig,date_valid,id_obs,lat,lon,vertical,id_var,value'
L_parameters =  ['TH', 'DBZH', 'RADAR_OBS_DISTANCE', 'RADAR_OBS_HEIGHT']
parameter2emet = {
        'DBZH': 'DBZ',
        'RADAR_OBS_DISTANCE': 'RADAR_OBS_DISTANCE',
        'RADAR_OBS_HEIGHT': 'RADAR_OBS_HEIGHT',
        'TH': 'DBZ',
        }

def worker_expand_for_EMET(input):
    fname = input
    output = [] # XXX
    filePath = '%s/%s' % (dir_npz, fname)
    arr = numpy.load(filePath)['array1']

    # pprint(arr) ; sys.exit() # XXX

    D_all = {}
    for a in arr:
        id_radarSTN = a['id_radarSTN']
        id_radar, id_stn = id_radarSTN[:5], id_radarSTN[5:]
        dt_emet = round_to_hour(a['datetime'].astype(datetime))
        dt_emet = dt_emet.strftime('%Y-%m-%d %H:%M:%S')

        D_all[id_radarSTN] = {
                'date_orig': dt_emet,
                'date_valid': dt_emet,
                'lat': D_stn[id_stn]['lat_emet'],
                'lon': D_stn[id_stn]['lon_emet'],
                'DBZH': translate_DBZ_BALTRAD_to_EMET(a['DBZH']),
                'TH': translate_DBZ_BALTRAD_to_EMET(a['TH']),
                'RADAR_OBS_DISTANCE': a['distance'],
                # height for verification is bin's minus radar's
                'RADAR_OBS_HEIGHT': a['height'] - D_radar[id_radar]['hgt']
                }

        # foo = D_all[id_radarSTN]
        # hgt = foo['RADAR_OBS_HEIGHT']
        # if hgt < 0:
        #    output.append('%s %s %-10s %-10s %s' % (id_radarSTN, dt_emet, a['TH'], a['DBZH'], hgt))

    L_var = L_parameters
    fp = {}
    for x in L_var:
        filePath = '%s/%s/%s_%s.txt' % (dir_emet, x, fname[:-4], x)
        fp[x] = open(filePath, 'wb')
        fp[x].write('%s\n' % header)

    for id_radarSTN in sorted(D_all):
        dt_emet = D_all[id_radarSTN]
        id_radar, id_stn = id_radarSTN[:5], id_radarSTN[5:]
        for var in L_parameters:
            # HACK
            # psycopg2.DataError: invalid input syntax for integer: ""
            # a201807220600_RADAR_OBS_HEIGHT.txt had '' for alt
            if 'alt' in D_stn[id_stn]:
                if D_stn[id_stn]['alt'] == '':
                    altitude = '0'
                else:
                    altitude = '%s' % D_stn[id_stn]['alt']
            else:
                altitude = '0'

            fp[var].write('%s,%s,%s,%s,%s,%4s,%s,%s\n' % (
                    dt_emet['date_orig'], dt_emet['date_valid'],
                    id_radarSTN,
                    D_stn[id_stn]['lat_emet'],
                    D_stn[id_stn]['lon_emet'],
                    altitude,    # XXX HACK alt of sfc obs stn, not RADAR_OBS_HEIGHT hgt relative to radar stn
                    parameter2emet[var],
                    dt_emet[var]))
    for x in L_var:
        fp[x].close()
    return output


def expand_for_EMET():
    '''
    '''
    for id_stn in D_stn:
        d = D_stn[id_stn]
        d['lon_emet'] = str(int(round(float(d['lon_d']) * 1e6)))
        d['lat_emet'] = str(int(round(float(d['lat_d']) * 1e6)))
    inputs = [x for x in sorted(os.listdir(dir_npz))
            if (x[:4] in ['2016'] and x[-4:] == '.npz')]
    # inputs = inputs[0:1] # XXX
    if sequential:
        outputs = []
        for input in inputs:
            outputs.append(worker_expand_for_EMET(input))
    else:
        pool = multiprocessing.Pool()    
        outputs = pool.map(worker_expand_for_EMET, inputs)
        pool.close()
        pool.join()

    # inspect outputs
    # foo = sorted(outputs)
    # fname = 'listing_%s.txt' % datetime.now().strftime('%Y%m%d%H%M')
    # with open(fname, 'wb') as f:
    #     for line in foo:
    #         f.write('%s\n' % line)
    # print 'see', fname


sequential = False # if True, avoid multiprocessing, see any stderr

if __name__ == '__main__':
    extract_point_values()
    expand_for_EMET()
