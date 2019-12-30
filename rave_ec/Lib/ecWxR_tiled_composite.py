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
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with RAVE.  If not, see <http://www.gnu.org/licenses/>.
'''

## Generate gemNA composite

## @file
## @author Daniel Michelson, Environment and Climate Change Canada
## @date 2016-09-13
import sys, os, glob, time, re, string, copy, dateutil.parser
import _rave, _raveio, _polarnav, _transform
import _cartesian, _cartesianvolume, _cartesianparam, _ravefield
import compositing
import rave_defines, rave_tempfile, rave_area, rave_tile_registry, area_registry
from Proj import dr, rd, c2s
import numpy as np
from xml.etree.ElementTree import Element, SubElement, Comment, tostring, parse
from xml.dom import minidom
import ec_filesys

GAIN, OFFSET = rave_defines.GAIN, rave_defines.OFFSET
NODATA, UNDETECT = 255.0, 0.0
PCSID, AREAID, AREA = 'gemNA', 'gemNA', None
#LUTFSTR = os.path.join(rave_defines.RAVEETC, '%s_tile_node_LUT.xml' % AREAID)
LUTFSTR = os.path.join(os.getenv("BLT_USER_PATH")+"/rave/etc", '%s_tile_node_LUT.xml' % AREAID)
RESIDENT_LUT = None
FSROOT = '/ssm/net/cmoi/apps/baltrad'  # Only for offline use
COMPROOT = FSROOT + '/output/composites'   # Only for offline use

initialized_lut, initialized_area = 0, 0


## Look-up table used to represent which radars contribute to which composite tiles. The look-up is written to XML file.
#  The ODIM 'node' is used for this, and the act of creating the XML file is done separately.  
class LUT(Element):

    ## Initializer
    # @param string name of the object's tag
    # @param string of the file name to use when writing the XML lookup
    def __init__(self, tag=None, lutfstr=LUTFSTR):
        self._children, self.attrib = [], {}  # These two attributes are lost when inheriting Element
        if tag: self.tag = tag
        self.lut_file = lutfstr

    ## Renames the LUT
    # @param string tag name
    def rename(self, name):
        self.tag = name

    ## Adds a comment to the LUT. (Isn't preserved so it can be ignored.)
    # @param string containing the comment to add
    def comment(self, comment):
        self.append(Comment(comment))

    ## Adds a SubElement to the LUT containing the list of ODIM nodes for that tile
    # @param string tag name
    # @param string text payload
    # @param dictionary containing attributes, e.g. uppler-left corner Y,X indices 
    def addSubElement(self, tag='Tiled area', text='', attrib={}):
        this = SubElement(self, tag)
        this.text = text
        this.attrib = copy.deepcopy(attrib)

    ## Adds a text value, e.g. an ODIM node, to a SubElement
    # @param string name of the SubElement
    # @param string value to add to the text payload
    # @param string delimiter to use when adding the new value to an existing payload
    def addText(self, SubElementName, value, delim=','):
        se = self.find(SubElementName)
        if se.text is None:
            se.text = value
        elif not len(se.text):
            se.text = value
        else: 
            se.text += '%s%s' % (delim, value)

    ## Checks whether the payload of an existing SubElement already contains a value
    # @param string name of the SubElement
    # @param string value to check
    # @returns boolean True if the value exists, otherwise False 
    def hasText(self, SubElementName, value):
        se = self.find(SubElementName)
        if se.text is None: return False
        return value in se.text

    ## Reads a LUT from XML file
    # @param string of the XML file to read
    def read(self, filename=LUTFSTR):
        e = parse(filename).getroot()
        if not self.tag: self.rename(e.tag)
        for c in e.getchildren():
            if not len(self.findall(c.tag)):
                self.addSubElement(c.tag, c.text, c.attrib)  # Does not work for Comments because they are functions

    ## Return a pretty-printed XML string for the Element.
    # @returns string XML representation of the contents of the LUT 
    def pretty(self):
        rough_string = tostring(self, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    ## Writes a LUT to XML file
    # @param string of the XML file to write
    def write(self, filename=LUTFSTR):
        fd = open(filename, 'w')
        fd.write(self.pretty())
        fd.close()


## Initializer for loading an existing LUT from XML file
def initLUT():
    global initialized_lut, RESIDENT_LUT
    if initialized_lut: return

    RESIDENT_LUT = LUT()
    RESIDENT_LUT.read()

    initialized_lut = 1

# Initialize
initLUT()


## Convenience function to create an empty LUT that can be written to file.
# @param string area identifier
# @returns LUT object
def makeLUT(areaid=AREAID):
    lut = LUT(areaid)
    #lut.comment('Author: Daniel Michelson')  # Comments can be written but I don't know how to read them

    for e in ['all', 'outside', 'undetermined']:
        lut.addSubElement(e)

    tiledefs = rave_tile_registry._registry[areaid]
    for tiledef in tiledefs:
        if re.match(areaid, tiledef.id):
            lut.addSubElement(tiledef.id)
        else:
            lut.addSubElement(areaid + "_" + tiledef.id)

    return lut


## Adds the subareas of a given area to the area registry to make them generally accessible.
# @param string area identifier
# @returns dictionary containing area identifiers as keys and their full area objects as items.
def addAreas(areaid=AREAID):
    area = rave_area._registry[areaid]
    xscale, yscale = area.xscale, area.yscale
    tiledefs = rave_tile_registry._registry[areaid]
    ark = rave_area._registry.keys()
    tile_areas = {}

    for tiledef in tiledefs:
        A = rave_area.AREA()
        if re.match(areaid, tiledef.id):
            A.Id = tiledef.id
        else:
            A.Id = areaid + "_" + tiledef.id
        A.name = "gemNA composite tile " + tiledef.id
        A.pcs = area.pcs.id
        A.extent = tiledef.extent
        A.xsize = int((tiledef.extent[2]-tiledef.extent[0])/area.xscale)
        A.ysize = int((tiledef.extent[3]-tiledef.extent[1])/area.yscale)
        A.xscale, A.yscale = xscale, yscale
        if A.Id not in ark:
            rave_area.register(A)  # This one may not be used in reality, but it should
        tile_areas[A.Id] = A
        # The following two lines seem to be necessary
        A.pcs = area.pcs
        area_registry.area._registry[A.Id] = A
    return tile_areas


## Initializes one Cartesian area and flags that this has been done
# @param string area identifier
def initArea(areaid=AREAID):
    global initialized_area, AREA
    if initialized_area: return

    AREA = rave_area._registry[areaid]

    initalized_area = 1


# Initialize our area
initArea()


## Helper for defining new areas.
# @param scan PolarScanCore object
# @param area rave_area.AREA instance
# @returns a rave_area.AREA instance for the single-site area
def MakeSingleAreaFromSCAN(scan, area=AREA):
    import numpy
    import _polarnav

    pn = _polarnav.new()
    pn.lon0, pn.lat0, pn.alt0 = scan.longitude, scan.latitude, scan.height
    maxR = scan.nbins * scan.rscale + scan.rscale # Add extra bin
    nrays = scan.nrays# * 2  # Doubled for greater accuracy

    minx =  10e100
    maxx = -10e100
    miny =  10e100
    maxy = -10e100

    azres = 360.0/nrays
    #az = 0.5*azres  # Start properly: half an azimuth gate from north
    az = 0.0  # Let's not and say we did ...
    while az < 360.0:
        latr, lonr = pn.daToLl(maxR, az*dr)
        herec = lonr*rd, latr*rd

        thislon, thislat = c2s([herec], area.pcs.id)[0]

        if thislon < minx: minx = thislon
        if thislon > maxx: maxx = thislon
        if thislat < miny: miny = thislat
        if thislat > maxy: maxy = thislat

        az+=azres

    # Expand to nearest pixel and buffer by one just to be sure
    dx = (maxx-minx) / area.xscale
    dx = (1.0-(dx-int(dx))) * area.xscale
    if dx < area.xscale:
        minx -= area.xscale + dx
        maxx += area.xscale
    dy = (maxy-miny) / area.yscale
    dy = (1.0-(dy-int(dy))) * area.yscale
    if dy < area.yscale:
        miny -= area.yscale + dy
        maxy += area.yscale

    xsize = int(round((maxx-minx)/area.xscale, 0))
    ysize = int(round((maxy-miny)/area.yscale, 0))

    A = rave_area.AREA()
    A.xsize, A.ysize, A.xscale, A.yscale = xsize, ysize, area.xscale, area.yscale
    A.extent = minx, miny, maxx, maxy
    A.pcs = area.pcs.id

    return A


## Helper function to determine if a radar covers any part of the destination area.
# @param tuple of floats representing the source area extent
# @param tuple of floats representing the destination area extent
# @returns boolean True if source radar covers any part of destination area, otherwise False
def isInside(sourceExtent, destExtent):
    LLx, LLy, URx, URy = sourceExtent
    ULx, ULy, LRx, LRy = LLx, URy, URx, LLy

    tllx, tlly, turx, tury = destExtent
    if ((LLx >= tllx and LLy >= tlly) and (LLx <= turx and LLy <= tury) or
        (ULx >= tllx and ULy >= tlly) and (ULx <= turx and ULy <= tury) or
        (URx >= tllx and URy >= tlly) and (URx <= turx and URy <= tury) or
        (LRx >= tllx and LRy >= tlly) and (LRx <= turx and LRy <= tury)):
        return True
    else: return False


## Determines to which tile the given pvol belongs. A pvol can belong
#  to more than one tile.
# @param filename input file string
# @param area object
# @param tile_areas dictionary containing area definitions for all tiles
# @param files_per_tile dictionary containing a list of file strings for each tile
def whichTile(filename, area, tile_areas, files_per_tile):
    path, fstr = os.path.split(filename)
    #node = fstr[:5].lower()  # according to ec_filesys.MakePolarFileName
    node = fstr.split(".")[-2].lower()  # according to ecWxR_qc

    if not RESIDENT_LUT.hasText("all", node):
        rio = _raveio.open(filename)
        scan = rio.object.getScanWithMaxDistance()

        scana = MakeSingleAreaFromSCAN(scan, area)

        # Does this radar cover any part of the full composite domain?
        inside = isInside(scana.extent, area.extent)
        if inside:
            for k in tile_areas.keys():
                if isInside(scana.extent, tile_areas[k].extent):
                    if not RESIDENT_LUT.hasText(k, node):
                        RESIDENT_LUT.addText(k, node)
                    files_per_tile[k].append(filename)
        else:
            RESIDENT_LUT.addText("outside", node)
        RESIDENT_LUT.addText("all", node)
    else:
        for k in tile_areas.keys():
            if RESIDENT_LUT.hasText(k, node):
                files_per_tile[k].append(filename)


## Generates composite based on a set of input files and an area identifier.
#  These two are combined in a list so that they can be pickled.
# @param args list containing a list of file strings, an area identifier, and
# a float representing the nominal date and time in seconds past epoch.
# @return string of resulting composite file.
def generate(args):
    TIME = args.pop()
    DATE = args.pop()
    areaid = args.pop()
    files = args.pop()

    start = time.time()  # For performance benchmarking
    
    comp = compositing.compositing()
    comp.filenames = files
    comp.detectors = "ropo,beamb,radvol-att,radvol-broad,distance,qi-total".split(",")
    comp.quantity = ["TH", "DBZH"]
#    comp.set_product_from_string("MAX")
    comp.set_product_from_string("PCAPPI")
    comp.range = 200000.0
    comp.gain = rave_defines.GAIN
    comp.offset = rave_defines.OFFSET
    comp.prodpar = 1000.0
    comp.set_method_from_string("HEIGHT_ABOVE_SEALEVEL")
    comp.qitotal_field = "pl.imgw.quality.qi_total"
    comp.pcsid = PCSID
    comp.xscale = AREA.xscale
    comp.yscale = AREA.yscale
    comp.zr_A = rave_defines.ZR_A
    comp.zr_b = rave_defines.ZR_b
    comp.applygapfilling = False
    comp.verbose = True
    comp.reprocess_quality_fields = False

    result = comp.generate(DATE, TIME, areaid)

    rio = _raveio.new()
    rio.object = result

    # Create temporary file in a place with write access
    rio.filename = rave_tempfile.mktemp(suffix='_%s_%sT%sZ.h5' % (areaid, DATE, TIME), close="True")[1]
    rio.save()

    end = time.time()

    return (rio.filename, end-start)


## Distributes 'generate' among six pre-defined tiles
#  @param fstrs list of input file name strings
#  @param DATE string nominal time of the product expressed as YYYYMMDD
#  @param TIME string nominal time of the product expressed as HHmmss
#  @param sequential Boolean, whether to process tiles sequentially, for debugging
#  @param int maximum range (km) beyond which data are excluded
#  @param Boolean return a RaveIOCore object (True) or not (False)
#  @returns string output (temporary) file name, or RaveIOCore object containing the composite
def multi_generate(fstrs, DATE, TIME, sequential=False, trim=0, return_rio=True):
    import multiprocessing
    
    if trim > 0:
        import ecWxR_trimRange
        ca, us = [], []  # Split up Canada and US
        for fstr in fstrs:
            path, filename = os.path.split(fstr)
            if filename[:2] == 'us': us.append(fstr)
            else: ca.append(fstr)
        trimmed = ecWxR_trimRange.multi_generate(us)
        fstrs = ca + trimmed

    args = []
    tile_areas, files_per_tile = addAreas(), {}

    for k in tile_areas.keys():
        files_per_tile[k] = []

    # Which files belong to which tiles?
    for fstr in fstrs:
        whichTile(fstr, AREA, tile_areas, files_per_tile)

    RESIDENT_LUT.write()  # Update the file on disk for the next time the composite is generated

    # Access each tile's list of input files
    for k in files_per_tile.keys():
        args.append([files_per_tile[k], k, DATE, TIME])
        #print k, files_per_tile[k]
    #sys.exit()  #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    results = []
    if not sequential:
        pool = multiprocessing.Pool(len(tile_areas.keys()))
        r = pool.map_async(generate, args, callback=results.append)
        r.wait() # Wait on the results
        pool.terminate()
        pool.join()
    else:
        for a in args:
            #print a[1]
            results.append(generate(a))
#    for i in range(len(results[0])):
#        print results[0][i]
    ocomp = mergeTiles(results[0])
    
    rio = _raveio.new()
    rio.object = ocomp
    if return_rio: return rio
    rio.filename = ec_filesys.MakeCompositeFileName(rio, root=COMPROOT, prefix='qcomp_v7_', makepath=True)
    rio.save()
    
    return rio.filename
    

## Merges a set of tiles into their associated composite. These tiles are written to (temporary) file before this
#  function is called.
# @param list of (temporary) input file strings containing tiles
# @returns Cartesian volume (composite) object 
def mergeTiles(fstrs):
    tiles = {}
    NODES = []
    qfields = 0  # Addressing Issue 33, we should be able to safely assume that
                 # output images always contain at least TH and DBZH, so reading
                 # the number of quality fields from DBZH should suffice
    qimage = None  # For initializing the output fields

    for fstr in fstrs:
        icomp = _raveio.open(fstr[0]).object  # Currently a tuple (fstr, time)
        areaid = icomp.source.split(',')[1].split(':')[1]
        try:
            nodes = eval(icomp.getAttribute('how/nodes'))
            for node in nodes:
                if not node in NODES:
                    NODES.append(node)
        except:
            pass
        image = icomp.getImage(0)
        tiles[areaid] = image

        nq = image.getParameter("DBZH").getNumberOfQualityFields()
        if nq > qfields:
            qfields = nq
            qimage = image
    NODES.sort()
    NODES = re.sub("[ \[\]]", "", str(NODES))

    # Initialize the output composite container
    ocomp = _cartesianvolume.new()
    ocomp.objectType = icomp.objectType
    ocomp.projection = icomp.projection
    ocomp.date = icomp.date
    ocomp.time = icomp.time
    ocomp.source = 'ORG:53,CMT:%s' % AREAID  # Canada

    oimage = _cartesian.new()
    
    a = rave_area.area(AREAID)
    ocomp.areaextent = a.extent
    ocomp.xscale, ocomp.yscale = a.xscale, a.yscale
    ocomp.addAttribute('how/nodes', NODES)

    # Initialize output fields if not present
    for p in qimage.getParameterNames():
        if p not in oimage.getParameterNames():
            param = qimage.getParameter(p)
            newp = _cartesianparam.new()
            newp.quantity = param.quantity
            newp.gain, newp.offset = param.gain, param.offset
            newp.nodata, newp.undetect = param.nodata, param.undetect
            data = np.zeros((a.ysize, a.xsize), np.uint8)
            if newp.nodata != 0: data += newp.nodata
            newp.setData(data)

            # Initialize quality fields too
            for i in range(param.getNumberOfQualityFields()):
                qf = param.getQualityField(i)
                newq = _ravefield.new()
                newq.setData(np.zeros((a.ysize, a.xsize), np.uint8))
                for attr in qf.getAttributeNames():
                    newq.addAttribute(attr, qf.getAttribute(attr))
                newp.addQualityField(newq)

            oimage.addParameter(newp)

    ocomp.addImage(oimage)

    # Now loop through input tiles and paste them into the output composite
    for areaid in tiles.keys():
        pasteTile(ocomp, tiles[areaid])

    # Delete temporary tile files
    for fstr in fstrs:
        os.remove(fstr[0])

    return ocomp


## Pastes a tile into the output composite
# @param Cartesian volume (composite) object of the tile
# @param Cartesian volume (composite) object of the composite into which the tile is being pasted
def pasteTile(ocomp, iimage):
    source = iimage.source.split(',')[1].split(':')[1] 
    ixsize, iysize = iimage.xsize, iimage.ysize

    e = RESIDENT_LUT.find(source)  # Returns an Element from the LUT containing the ODIM nodes per tile
    ULy, ULx = eval(e.attrib["upper_left_yx"])  # These are the Y,X indices 
    LRy, LRx = ULy + iysize, ULx + ixsize

    # Paste in one parameter at a time
    for p in iimage.getParameterNames():
        iparam = iimage.getParameter(p)
        oparam = ocomp.getImage(0).getParameter(p)
        ipdata = iparam.getData()
        opdata = oparam.getData()
        opdata[ULy:LRy,ULx:LRx] = ipdata.astype(opdata.dtype)
        oparam.setData(opdata)
        
        # Paste in the quality fields
        for i in range(iparam.getNumberOfQualityFields()):
            iqf = iparam.getQualityField(i)
            task = iqf.getAttribute('how/task')
            oqf = oparam.getQualityFieldByHowTask(task)
            iqfdata, oqfdata = iqf.getData(), oqf.getData()
            oqfdata[ULy:LRy,ULx:LRx] = iqfdata.astype(oqfdata.dtype)
            oqf.setData(oqfdata)


## Selects files closest to nominal time, assuming there are multiple inputs
#  from a single radar in an input list of file strings
# @param list input file strings
# @param string ISO 8601 time
# @return list of file strings with which to composite
def selectFiles(flist, timestamp):
    # Get nominal date and time for this set of files
    if timestamp[-1].upper() != "Z": timestamp += "Z"
    nominal = dateutil.parser.parse(timestamp)

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


if __name__ == "__main__":
    pass
