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
------------------------------------------------------------------------*/

Tests the DOPVOL QC functionality

@file
@author Daniel Michelson, Environment and Climate Change Cananda
@date 2016-06-10
'''
import unittest
import os
import _raveio
import _rave
import _rave_ec
import ec_dopvolqc
import ec_quality_plugin
from numpy import *

class PyDopvolQCTest(unittest.TestCase):
    FIXCONVOL   = "fixtures/201605181200~~CONVOL_URP_WWW_RADAR_IRIS_20160518120016.h5"
    FIXDOPVOL1A = "fixtures/201605181200~~DOPVOL1_A_URP_WWW_RADAR_IRIS_20160518120128.h5"
    FIXDOPVOL1B = "fixtures/201605181200~~DOPVOL1_B_URP_WWW_RADAR_IRIS_20160518120247.h5"
    FIXDOPVOL1C = "fixtures/201605181200~~DOPVOL1_C_URP_WWW_RADAR_IRIS_20160518120405.h5"
    FIXDOPVOL2  = "fixtures/201605181200~~DOPVOL2_URP_WWW_RADAR_IRIS_20160518120442.h5"
    REF_OUT     = "fixtures/reference_dopvolFilter.h5"
    REF_DOPVOL  = "fixtures/dopvol.h5"
    BADINPUT    = "fixtures/bad_fixture.h5"
  
    def setUp(self):
        pass

    def tearDown(self):
        pass


    def testMergeDopvol(self):
        dopvol1a = _raveio.open(self.FIXDOPVOL1A).object
        dopvol1b = _raveio.open(self.FIXDOPVOL1B).object
        dopvol1c = _raveio.open(self.FIXDOPVOL1C).object
        dopvol2  = _raveio.open(self.FIXDOPVOL2).object
        dvol = ec_dopvolqc.mergeDopvol(dopvol1a, dopvol1b, dopvol1c, dopvol2)
        dopvol = _raveio.open(self.REF_DOPVOL).object
        this = dvol.getScan(0)
        ref = dopvol.getScan(0)
        status = different(this, ref, "VRADH")
        self.assertFalse(status)


    def testDopvolFilter(self):
        convol = _raveio.open(self.FIXCONVOL).object
        dopvol = _raveio.open(self.REF_DOPVOL).object
        refvol = _raveio.open(self.REF_OUT).object

        ec_dopvolqc.dopvolFilter(convol, dopvol)

        cdat = convol.getScan(23)
        cref = refvol.getScan(23)

        status = different(cdat, cref)
        self.assertFalse(status)


    # No Nyquist!
    def testWrongInput(self):
        dscan = _raveio.open(self.BADINPUT).object
        cscan = _raveio.open(self.FIXCONVOL).object.getScan(23)

        status = _rave_ec.dopvolFilter(cscan, dscan, 1)
        self.assertFalse(status)


    def testDopvolFilterQualityPlugin_getQualityFields(self):
        dvfp = ec_quality_plugin.ec_dopvolFilter_plugin()
        id = dvfp.getQualityFields()[0]
        self.assertEqual(id, "ca.ec.filter.dopvol-clutter")


    def testNoTH(self):
        convol = _raveio.open(self.FIXCONVOL).object
        dopvol = _raveio.open(self.REF_DOPVOL).object
        for i in range(convol.getNumberOfScans()):
            scan = convol.getScan(i)
            scan.removeParameter('TH')
        try:
            ec_dopvolqc.dopvolFilter(convol, dopvol)
            self.fail()
        except:
            self.assertTrue(True)


    def testNoVRADH(self):
        convol = _raveio.open(self.FIXCONVOL).object
        dopvol = _raveio.open(self.REF_DOPVOL).object
        for i in range(dopvol.getNumberOfScans()):
            scan = dopvol.getScan(i)
            scan.removeParameter('VRADH')
        try:
            ec_dopvolqc.dopvolFilter(convol, dopvol)
            self.fail()
        except:
            self.assertTrue(True)


    def testDopvolFilterQualityPlugin(self):
        convol = _raveio.open(self.FIXCONVOL).object
        dopvol = _raveio.open(self.REF_DOPVOL).object
 
        ec_dopvolqc.dopvolFilter(convol, dopvol)
        cdat1 = convol.getScan(23)
         
        dvfp = ec_quality_plugin.ec_dopvolFilter_plugin()
        convol = _raveio.open(self.FIXCONVOL).object  # re-read
        dvfp.process(convol, False, arguments=[self.FIXDOPVOL1A,self.FIXDOPVOL1B,self.FIXDOPVOL1C,self.FIXDOPVOL2])
 
        cdat2 = convol.getScan(23)
        status = different(cdat1, cdat2)
        self.assertFalse(status)
        
    
def different(scan1, scan2, param="DBZH"):
    a = scan1.getParameter(param).getData()
    b = scan2.getParameter(param).getData()
    c = a == b
    d = sum(where(equal(c, False), 1, 0).flat)
    if d > 0:
        return True
    else:
        return False 
