#!/usr/bin/python
'''
permissions issue when Ahmed had log file here
/fs/site1/dev/eccc/mrd/armp/bha001/dbm001/ssm/baltrad_18.04_ubuntu-14.04-amd64-64/rave/etc
soln : moved etc, made own one
/fs/site1/dev/eccc/mrd/armp/bha001/dbm001/ssm/baltrad_18.04_ubuntu-14.04-amd64-64/rave/bin/ecWxR_qc

NOTE earlier version of this script had a dozen warning tests, only a couple ever
threw mesages (ergo the data are generally reliable); most removed, can refer to 
./archive/verify_0.py


in 201608 these lowest sweeps always had height bin below radar itself
[u'caxamCYBC -318.0', u'caxamCYYY -277.0', u'caxamKFVE -41.0'],  metres
hgt caxam   732.0,  -67.600890, 48.480550, Valdirene QC
     CYBC   CYBC,49.1200,-68.2000,21
     CYYY   CYYY,48.6200,-68.2000,52
     KFVE   KFVE,47.2800,-68.3200,85

'''
# TODO add ord_soumet for reliable performance (KOn offers to help)

from datetime import datetime
import csv
import multiprocessing
import os
import sys
import time

from config import verifroot
from config import dir_store # stored QC'ed radar data

from pprint import pprint, pformat

# BALTRAD tools
import Proj
import _polarscan
import _polarvolume
import _rave
import _raveio

timestamp = datetime.utcnow().strftime('%Y%m%d%H%M')

from pdb import set_trace

def load_station():
    '''read EMET config file, provided by Francois: CYUL,45.4700,-73.7300,36
    '''
    D_stn = {}
    with open(verifroot+'/station.csv', 'rb') as f:
        reader = csv.reader(f)
        next(reader, None)    # skip header
        for id_stn, lat_d, lon_d, alt in reader:
            lonlat = Proj.d2r((float(lon_d), float(lat_d)))
            D_stn[id_stn] = {'lonlat': lonlat,
                    'lon_d': lon_d, 'lat_d': lat_d, 'alt': alt}
    return D_stn


def worker_collect_radar_metadata(input=None):
    directory = input
    D_metadata = {}
    for fname in os.listdir(directory):
        try:
            filePath = os.path.join(directory, fname)
            rio = _rave.open(filePath)    # use ODIM h5 functionality
            obj = rio.object
            if not _polarvolume.isPolarVolume(obj):    # rarely happened
                sys.stderr.write('Warning: not polar volume: %s\n' % filePath)
                continue
            source = obj.source
            sourceTuple = source.split(',')
            id_radar = sourceTuple[0].split(':')[1]
            # NOTE ussox threw error for 2019 data
            plc = sourceTuple[1].split(':')[1]
            D_metadata[id_radar] = {
                    'lon': obj.longitude, 'lat': obj.latitude,
                    'hgt': obj.height, 'plc': plc,
                    }
        except:
            sys.stderr.write('Warning, failed for %s\n' % fname)
            # Level2_KMQT_20180510_0204.ar2v.qc.usmqt.h5
            # Level2_KRGX_20180520_1501.ar2v.qc.usrgx.h5
    return D_metadata


def collect_radar_metadata():
    directories = ['%s/%s' % (dir_store, x) for x in os.listdir(dir_store)
            if x[:6] == '201607']

    # 201607010* made same metadata as for all of 201607*
    # directories = ['%s/%s' % (dir_store, x) for x in os.listdir(dir_store)
    #        if x[:9] == '201607010'] # XXX

    pool = multiprocessing.Pool()    
    outputs = pool.map(worker_collect_radar_metadata, directories)
    pool.close()
    pool.join()
    D_metadata = {}
    for output in outputs:
        for id_radar in output:
            if id_radar not in D_metadata:
                d = output[id_radar]
                D_metadata[id_radar] = d
                ll = Proj.r2d((d['lon'], d['lat']))
                D_metadata[id_radar].update({
                    'lon_d' : ll[0],
                    'lat_d' : ll[1],
                    })
            # else:      # could check radar metadata consistency between h5 files, but
            #    pass    # assume all in set have same metadata
    fname_out = verifroot+'/metadata/radar_metadata_%s.csv' % timestamp
    with open(fname_out, 'wb') as f:
        for id_radar in sorted(D_metadata):
            d = D_metadata[id_radar]
            lonlat = '%r,%r,' % (d['lon'], d['lat'])
            f.write('%s,%s%s %6.1f, %11.6f, %9.6f, %s\n' % (
                id_radar, lonlat, ' '*(40-len(lonlat)),
                d['hgt'], d['lon_d'], d['lat_d'], d['plc']))
    os.symlink(fname_out, verifroot+'/radar.csv')
    return D_metadata


def load_radar():
    if os.path.isfile(verifroot+'/radar.csv'):
        D_radar = {}
        with open(verifroot+'/radar.csv', 'rb') as f:
            reader = csv.reader(f)
            for x in csv.reader(f):
                D_radar[x[0].strip()] = {
                        'lon': float(x[1]), 'lat': float(x[2]),
                        'hgt': float(x[3]),
                        'lon_d': float(x[4]), 'lat_d': float(x[5]),
                        'plc': x[6].strip(),}
    else:
        D_radar = collect_radar_metadata()
    return D_radar

# TODO pathFname have verifroot

def match_radars_to_stations(print_summary=False):
    # RADIUS_THRESHOLD = 250000.    # only map radars to stations within
    RADIUS_THRESHOLD = 247000.    # Warning_nIN : nearestIndex None, casra CYYN, dist = 247183.26
    D_stn = load_station()
    D_radar = load_radar()

    obj = _polarscan.new()
    for id_stn in D_stn:
        D_stn[id_stn]['radars'] = []
    for id_radar in D_radar:
        D_radar[id_radar]['stations'] = []

    for id_radar in D_radar:
        d_radar = D_radar[id_radar]
        obj.longitude, obj.latitude = d_radar['lon'], d_radar['lat']
        for id_stn in D_stn:
            d_stn = D_stn[id_stn]
            distance = obj.getDistance(d_stn['lonlat'])
            if distance <= RADIUS_THRESHOLD:
                d_radar['stations'].append(id_stn)
                d_stn['radars'].append(id_radar)
    fname_out = verifroot+'/metadata/radar_station_metadata_%s.csv' % timestamp
    with open(fname_out, 'wb') as f:
        for id_radar in sorted(D_radar):
            if D_radar[id_radar]['stations']:  # skip Guam, no stations
                f.write('%s' % id_radar)
                for id_stn in D_radar[id_radar]['stations']:
                    f.write(',%s' % id_stn)
                f.write('\n')
    os.symlink(fname_out, verifroot+'/radar_station.csv')

    if print_summary:
        L_num_radar = sorted([[len(D_radar[id_radar]['stations']), id_radar]
                for id_radar in D_radar], reverse=True)
        L_num_stn = sorted([[len(D_stn[id_stn]['radars']), id_stn]
                for id_stn in D_stn], reverse=True)
        eff_radar_count = sum([x[0] for x in L_num_stn])
        eff_stn_count = sum([x[0] for x in L_num_radar])
        if eff_radar_count != eff_stn_count:
            sys.stderr.write('Error : radar and station indexes disagree\n')
            sys.exit(1)
        fname_out = 'radar_station_summary_%s.txt' % timestamp
        with open(fname_out, 'wb') as f:
            f.write('%d radars and %d stations give %d radar-station pairs\n' % (
                    len(D_radar), len(D_stn), eff_radar_count))
            for n, id_radar in L_num_radar:
                f.write('%s  %d\n' % (id_radar, n))
            for n, id_stn in L_num_stn:
                f.write('%s  %d\n' % (id_stn, n))
        print 'see radar-station pair summary :', fname_out


def load_radar_station():
    if not os.path.isfile(verifroot+'/radar_station.csv'):
        match_radars_to_stations(print_summary=True)
    D_radar_station = {}
    with open(verifroot+'/radar_station.csv', 'rb') as f:
        for line in f.readlines():
            line = line.rstrip()    # remove '\n'
            x = line.split(',')
            D_radar_station[x[0]] = x[1:]    # may be empty, e.g., usgua
    return D_radar_station


if __name__ == '__main__':
    #  D_stn = load_station()
    # pprint(D_stn) ; sys.exit() # XXX
    # D_radar = load_radar()
    # pprint(D_radar) ; sys.exit()
    D_radar_station = load_radar_station()
    # pprint(D_radar_station) ; sys.exit()
