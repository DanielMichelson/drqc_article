/* --------------------------------------------------------------------
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
/** Header file representing miscellaneous functionality for processing
 * Canadian and American data.
 * @file
 * @author Daniel Michelson, Environment and Climate Change Cananda
 * @date 2016-06-01
 */
#ifndef RAVEEC_H
#define RAVEEC_H

#include "polarvolume.h"
#include "polarscan.h"
#include "polarscanparam.h"
#include "polarnav.h"
#include "rave_field.h"
#include "rave_attribute.h"
#include "rave_object.h"
#include "rave_list.h"
#include "rave_alloc.h"
#include "rave_types.h"
#include "raveutil.h"
#include "rave_debug.h"


/**
* Helper function : adds a double-precision floating point attribute to an ODIM object.
* @param[in] object - Toolbox RaveField_t object, either a polar volume or polar scan
* @param[in] name - string containing the ODIM attribute name, e.g. something starting with 'how/'
* @param[in] value - double-precision floating point value
* @return signed integer status indicator (zero means success)
*/
int addDoubleAttribute(RaveField_t* object, const char* name, double value);

/**
 * Helper function : adds a string attribute to an ODIM object.
 * @param[in] object - Toolbox RaveField_t object, either a polar volume or polar scan
 * @param[in] name - string containing the ODIM attribute name, e.g. something starting with 'how/'
 * @param[in] value - string (unterminated)
 * @return signed integer status indicator (zero means success)
 */
int addStringAttribute(RaveField_t* object, const char* name, const char* value);


/**
 * CANADIAN: performs DOPVOL filtering of the CONVOL.
 * @param[in] convol - input scan from the CONVOL, containing TH
 * @param[in] dopvol - input scan from the DOPVOL, containing VRADH
 * @param[in] SPATIAL - int where 1=perform spatial filter, 0=don't
 * @return int 1 if successful, otherwise 0
 */
int dopvolFilter(PolarScan_t* convol, PolarScan_t* dopvol, int SPATIAL);

/**
 * Calculates standard deviation of reflectivity in the vertical as a measure of texture.
 * Relies on a pre-initiated field for storing the per-bin texture.
 * @param[in] pvol - input (CONVOL) polar volume containing reflectivity
 * @param[in] etop - input scan containing echo-top info, used to constrain the calculations
 * @param[in] vtfield - field object that will be populated with standard deviation
 * @param[in] paramname - string of the reflectivity quantity to process: TH or DBZH
 * @return int 1 if successful, otherwise 0
 */
int verticalTexture(PolarVolume_t* pvol, PolarScan_t* etop, RaveField_t* vtfield, const char* paramname);

/**
 * Smooths the echo-top field using a median filter
 * @param[in] etop - input scan containing echo-top data
 * @param[in] raypad - how much azimuthal one-way padding in the filtering kernel
 * @param[in] binpad - how much one-way padding in range in the filtering kernel
 * @return in 1 if successful, otherwise 0
 */
int echotopMedian(PolarScan_t* etop, int raypad, int binpad);

/**
 * Performs a filtering of reflectivity data based on the echo-top field.
 * Echoes that are above a reflectivity threshold must also be above a
 * height threshold in order to be considered "real".
 * @param[in] zscan - input scan, containing either TH or DBZH
 * @param[in] etop - input scan, containing either HGHT
 * @param[in] zthresh - reflectivity threshold value
 * @param[in] hthresh - echo-top height (km) threshold value
 * @param[in] paramname - string of the reflectivity quantity to process: TH or DBZH
 * @return int 1 if successful, otherwise 0
 */
int echotopFilter(PolarScan_t* zscan, PolarScan_t* etop, double zthresh, double hthresh, const char* paramname);

#endif /* RAVEEC_H */
