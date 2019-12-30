#PR hack of wradlib-wradlib-6c2a093c8a04/build/lib/wradlib/io.py
#!/usr/bin/env python

# standard libraries

import sys
from collections import OrderedDict
import os
import warnings

import numpy as np
import ec_RB_util as util

def find_key(key, dictionary):
    """Searches for given key in given (nested) dictionary.

    Returns all found parent dictionaries in a list.

    Parameters
    ----------
    key : string
        the key to be searched for in the nested dict
    dictionary : dict
        the dictionary to be searched

    Returns
    -------
    output : a dictionary or list of dictionaries

    """
    for k, v in dictionary.iteritems():
        if k == key:
            yield dictionary
        elif isinstance(v, dict):
            for result in find_key(key, v):
                yield result
        elif isinstance(v, list):
            for d in v:
                for result in find_key(key, d):
                    yield result


def decompress(data):
    """Decompression of data

    Parameters
    ----------
    data : string (from xml)
        data string containing compressed data.
    """
    zlib = util.import_optional('zlib')
    return zlib.decompress(data)


def get_RB_data_layout(datadepth):
    """Calculates DataWidth and DataType from given DataDepth of RAINBOW radar data

    Parameters
    ----------
    datadepth : int
        DataDepth as read from the Rainbow xml metadata.

    Returns
    -------
    datawidth : int
        Width in Byte of data

    datatype : string
        conversion string .

    """

    if sys.byteorder != 'big':
        byteorder = '>'
    else:
        byteorder = '<'

    datawidth = datadepth / 8

    """
    2015-Oct, PR: Add fake for  <flagmap blobid="1" rows="500" columns="500" depth="1">
    if datadepth == 1:
        datawidth = 1
    """

    if datawidth in [1, 2, 4]:
        datatype = byteorder + 'u' + str(datawidth)
    else:
        raise ValueError("Wrong DataDepth: %d. Conversion only for depth 8, 16, 32" % datadepth)

    return datawidth, datatype


def get_RB_data_attribute(xmldict, attr):
    """Get Attribute `attr` from dict `xmldict`

    Parameters
    ----------
    xmldict : dict
        Blob Description Dictionary

    attr : string
        Attribute key

    Returns
    -------
    sattr : int
        Attribute Values

    """

    try:
        sattr = int(xmldict['@' + attr])
    except KeyError:
        if attr == 'bins':
            sattr = None
        else:
            raise KeyError('Attribute @' + attr + ' is missing from Blob Description'
                                                  'There may be some problems with your file')
    return sattr


def get_RB_blob_attribute(blobdict, attr):
    """Get Attribute `attr` from dict `blobdict`

    Parameters
    ----------
    blobdict : dict
        Blob Description Dictionary

    attr : string
        Attribute key

    Returns
    -------
        Attribute Value

    """
    try:
        value = blobdict['BLOB']['@' + attr]
    except KeyError:
        raise KeyError('Attribute @' + attr + ' is missing from Blob.' +
                       'There may be some problems with your file')

    return value


def get_RB_blob_data(datastring, blobid):
    """ Read BLOB data from datastring and return it

    Parameters
    ----------
    datastring : dict
        Blob Description Dictionary

    blobid : int
        Number of requested blob

    Returns
    -------
    data : string
        Content of blob

    """
    xmltodict = util.import_optional('xmltodict')

    start = 0
    if sys.version_info[1] == 6:
        searchString = r'<BLOB blobid="{0}"'.format(blobid)
    else:
        searchString = r'<BLOB blobid="{}"'.format(blobid)
    start = datastring.find(searchString, start)
    if start == -1:
        raise EOFError('Blob ID {} not found!'.format(blobid))
    end = datastring.find('>', start)
    xmlstring = datastring[start:end + 1]

    # cheat the xml parser by making xml well-known
    xmldict = xmltodict.parse(xmlstring + '</BLOB>')
    cmpr = get_RB_blob_attribute(xmldict, 'compression')
    size = int(get_RB_blob_attribute(xmldict, 'size'))
    data = datastring[end + 2:end + 2 + size]  # read blob data to string

    # decompress if necessary
    # the first 4 bytes are neglected for an unknown reason
    if cmpr == "qt":
        data = decompress(data[4:])

    return data


def map_RB_data(data, datadepth):
    """ Map BLOB data to correct DataWidth and Type and convert it to numpy array

    Parameters
    ----------
    data : string
        Blob Data

    datadepth : int
        bit depth of Blob data

    Returns
    -------
    data : numpy array
        Content of blob

    """
    datawidth, datatype = get_RB_data_layout(datadepth)

    # import from data buffer well aligned to data array
    data = np.ndarray(shape=(len(data) / datawidth,), dtype=datatype, buffer=data)

    return data


def get_RB_blob_from_string(datastring, blobdict):
    """
    Read BLOB data from datastring and return it as numpy array with correct
    dataWidth and shape

    Parameters
    ----------
    datastring : dict
        Blob Description Dictionary

    blobdict : dict
        Blob Dict

    Returns
    -------
    data : numpy array
        Content of blob as numpy array

    """

    blobid = get_RB_data_attribute(blobdict, 'blobid')
    data = get_RB_blob_data(datastring, blobid)

    # map data to correct datatype and width
    datadepth = get_RB_data_attribute(blobdict, 'depth')
    data = map_RB_data(data, datadepth)

    # reshape data
    bins = get_RB_data_attribute(blobdict, 'bins')
    if bins:
        rays = get_RB_data_attribute(blobdict, 'rays')
        data.shape = (rays, bins)

    return data


def get_RB_blob_from_file(filename, blobdict):
    """
    Read BLOB data from file and return it with correct
    dataWidth and shape

    Parameters
    ----------
    filename : string
        Filename of Data File

    blobdict : dict
        Blob Dict

    Returns
    -------
    data : numpy array
        Content of blob as numpy array

    """
    try:
        fid = open(filename, "rb")
    except IOError:
        print "WRADLIB: Error opening Rainbow file ", filename
        raise IOError

    datastring = fid.read()
    fid.close()

    data = get_RB_blob_from_string(datastring, blobdict)

    return data


def get_RB_file_as_string(filename):
    """ Read Rainbow File Contents in dataString

    Parameters
    ----------
    filename : string
        Filename of Data File

    Returns
    -------
    dataString : string
        File Contents as dataString

    """
    try:
        fid = open(filename, "rb")
    except IOError:
        print "WRADLIB: Error opening Rainbow file ", filename
        raise IOError

    dataString = fid.read()
    fid.close()

    return dataString


def get_RB_blobs_from_file(filename, rbdict):
    """Read all BLOBS found in given nested dict, loads them from file
    given by filename and add them to the dict at the appropriate position.

    Parameters
    ----------
    :param filename: string
        Filename of Data File
    :param rbdict: dict
        Rainbow file Contents

    Returns
    -------
    :rtype : dict
        Rainbow File Contents

    """

    blobs = list(find_key('@blobid', rbdict))

    datastring = get_RB_file_as_string(filename)
    for blob in blobs:
        data = get_RB_blob_from_string(datastring, blob)
        blob['data'] = data

    return rbdict


def get_RB_header(filename):
    """Read Rainbow Header from filename, converts it to a dict and returns it

    Parameters
    ----------
    filename : string
        Filename of Data File

    Returns
    -------
    object : dictionary
        Rainbow File Contents

    """
    try:
        fid = open(filename, "rb")
    except IOError:
        print "WRADLIB: Error opening Rainbow file ", filename
        raise IOError

    # load the header lines, i.e. the XML part
    endXMLmarker = "<!-- END XML -->"
    header = ""
    line = ""
    while not line.startswith(endXMLmarker):
        header += line[:-1]
        line = fid.readline()
        if len(line) == 0:
            break

    fid.close()

    xmltodict = util.import_optional('xmltodict')
    return xmltodict.parse(header)


def read_Rainbow(filename, loaddata=True):
    """"Reads Rainbow files files according to their structure

    In contrast to other file readers under wradlib.io, this function will *not* return
    a two item tuple with (data, metadata). Instead, this function returns ONE
    dictionary that contains all the file contents - both data and metadata. The keys
    of the output dictionary conform to the XML outline in the original data file.

    The radar data will be extracted from the data blobs, converted and added to the
    dict with key 'data' at the place where the @blobid was pointing from.

    Parameters
    ----------
    filename : string (a rainbow file path)

    Returns
    -------
    rbdict : a dictionary that contains both data and metadata according to the
              original rainbow file structure
    """

    rbdict = get_RB_header(filename)

    if loaddata:
        rbdict = get_RB_blobs_from_file(filename, rbdict)

    return rbdict

if __name__ == '__main__':
    print 'wradlib: Calling module <io> as main...'
