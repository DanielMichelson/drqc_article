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
/** Miscellaneous functionality for processing Canadian and American data.
 * @file
 * @author Daniel Michelson, Environment and Climate Change Cananda
 * @date 2016-06-01
 */
#include "raveec.h"


int addDoubleAttribute(RaveField_t* object, const char* name, double value) {
	int ret = 0;
	RaveAttribute_t* attr;
	attr = RaveAttributeHelp_createDouble(name, value);
	ret = RaveField_addAttribute(object, attr);
	RAVE_OBJECT_RELEASE(attr);
	return ret;
}


int addStringAttribute(RaveField_t* object, const char* name, const char* value) {
	int ret = 0;
	RaveAttribute_t* attr;
	attr = RaveAttributeHelp_createString(name, value);
	ret = RaveField_addAttribute(object, attr);
	RAVE_OBJECT_RELEASE(attr);
	return ret;
}


void initNavinfo(PolarNavigationInfo* navinfo) {
	navinfo->lon = 0.0;
	navinfo->lat = 0.0;
	navinfo->height = 0.0;
	navinfo->actual_height = 0.0;
	navinfo->distance = 0.0;
	navinfo->range = 0.0;
	navinfo->azimuth = 0.0;
	navinfo->elevation = 0.0;
	navinfo->ei = 0;
	navinfo->ri = 0;
	navinfo->ai = 0;
}


int dopvolFilter(PolarScan_t* convol, PolarScan_t* dopvol, int SPATIAL) {
	PolarScanParam_t* TH = NULL;
	PolarScanParam_t* DBZH = NULL;
	PolarScanParam_t* VRADH = NULL;
	RaveAttribute_t* attr = NULL;
	RaveField_t* qfield = NULL;
	double gain = 1.0 / 255.0;  /* used to scale data quality */
	int r, b, nrays, nbins, dnrays, dnbins, lr, lb, lrays, lbins, tr, hits, n;
	double crscale, drscale, ni, vthresh, th, vradh, undetect;
	double sum, mean, quality;
	double lon, lat;
	RaveValueType rvt_th, rvt_vradh;
	PolarNavigationInfo navinfo;
	const char* qidentifier = "ca.ec.filter.dopvol-clutter";
	int ret = 1;  /* exit code */
	initNavinfo(&navinfo);   /* shut up the compiler */

	if (PolarScan_hasParameter(convol, "TH")) {
		TH = PolarScan_getParameter(convol, "TH");
	} else {
		RAVE_ERROR0("CONVOL contains no TH quantity. Bailing ...");
		return 0;
	}
	if (!PolarScan_hasParameter(convol, "DBZH")) {
		DBZH = RAVE_OBJECT_CLONE(TH);
		PolarScanParam_setQuantity(DBZH, "DBZH");
	} else {
		DBZH = PolarScan_getParameter(convol, "DBZH");
	}
	if (!PolarScan_hasParameter(dopvol, "VRADH")) {  /* Check for completeness ... */
		RAVE_ERROR0("DOPVOL contains no VRADH quantity. Bailing ...");
		ret = 0;
		goto done;
	}

	/* This QC has already been performed if the QC attribute exists, so don't redo it */
	qfield = PolarScan_getQualityFieldByHowTask(convol, qidentifier);
	if (qfield) {
		RAVE_ERROR0("DOPVOL QC has already been performed. Will not be redone.");
		ret = 0;
		goto done;
	} else {
		qfield = RAVE_OBJECT_NEW(&RaveField_TYPE);
	}

	if (SPATIAL) VRADH = PolarScan_getParameter(dopvol, "VRADH");

	nrays = PolarScan_getNrays(convol);
	nbins = PolarScan_getNbins(convol);
	dnrays = PolarScan_getNrays(dopvol);
	dnbins = PolarScan_getNbins(dopvol);
	crscale = PolarScan_getRscale(convol);
	drscale = PolarScan_getRscale(dopvol);

	RaveField_createData(qfield, (long)nbins, (long)nrays, RaveDataType_UCHAR);
	addDoubleAttribute(qfield, "what/gain", gain);
	addDoubleAttribute(qfield, "what/offset", 0.0);
	addStringAttribute(qfield, "how/task", qidentifier);

	attr = PolarScan_getAttribute(dopvol, "how/NI");  /* Nyquist interval */
	if (attr) {
		RaveAttribute_getDouble(attr, &ni);
	} else {
		RAVE_ERROR0("No Nyquist interval in metadata (how/NI). Cannot continue.");
		ret = 0;
		goto done;
	}
	vthresh = 2 * ni / 127.0;  /* Velocity threshold used to filter reflectivities */
	undetect = PolarScanParam_getUndetect(TH);

	for (r=0;r<nrays;r++) {
		for (b=0;b<nbins;b++) {

			/* Initialize qfield to 1, which is scaled to 255 */
			RaveField_setValue(qfield, b, r, 255.0);

			rvt_th =  PolarScanParam_getConvertedValue(TH, b, r, &th);
			if (rvt_th == RaveValueType_DATA) {
				PolarScan_getLonLatFromIndex(convol, b, r, &lon, &lat);

				rvt_vradh = PolarScan_getNearestConvertedParameterValue(dopvol, "VRADH", lon, lat, &vradh, &navinfo);

				/* Out-of-bounds check */
				if ( (navinfo.ai == -1) || (navinfo.ri == -1) ) continue;

				/* Filter based on nearest velocity */
				if (SPATIAL != 1) {
					if ( (rvt_vradh != RaveValueType_DATA) || ( (rvt_vradh == RaveValueType_DATA) && (fabs(vradh) <= vthresh) ) ) {
						PolarScanParam_setValue(DBZH, b, r, undetect);
						RaveField_setValue(qfield, b, r, 0.0);
					}

				/* Filter based on a spatial kernel, accounting for azimuthal wrap-around */
				} else {
					/* Determine polar kernel. nrays can be ~360 or ~720.
					 * rscale can be 500 or 1000 m */
					if (nrays > 600) lrays = 4;
					else lrays = 2;
					if ( (crscale/drscale) > 1.0 ) lbins = 4;
					else lbins = 2;

					hits = 0;
					n = 0;
					sum = 0.0;
					mean = 0.0;
					quality = 1.0;

					for (lr=navinfo.ai-lrays ; lr<=navinfo.ai+lrays ; lr++) {
						if (lr < 0) {
							tr = (dnrays-1) + lr;
						} else if (lr >= dnrays) {
							tr = lr - dnrays;
						} else tr = lr;

						for (lb=navinfo.ri-lbins ; lb<=navinfo.ri+lbins ; lb++) {
							/* In-range while in loop check */
							if ( (lb >= 0) && (lb < dnbins) ) {
								rvt_vradh = PolarScanParam_getConvertedValue(VRADH, lb, tr, &vradh);
								n += 1;

								if (rvt_vradh == RaveValueType_DATA) {
									sum += fabs(vradh);  /* we don't want an artificially wide isodop */
									hits += 1;
								}
							}
						}
					}
					if (hits > 0) {
						mean = sum / hits;
						quality = (double)hits / (double)n;
					} else {
						mean = 0.0;
						quality = 0.0;
					}
					if ( (n>0) && (mean <= vthresh) ) {
						PolarScanParam_setValue(DBZH, b, r, undetect);
					}
					RaveField_setValue(qfield, b, r, quality/gain);
				}
			}
		}
	}
	PolarScan_addQualityField(convol, qfield);
	PolarScan_addParameter(convol, DBZH);
done:
	RAVE_OBJECT_RELEASE(TH);
	RAVE_OBJECT_RELEASE(DBZH);
	RAVE_OBJECT_RELEASE(VRADH);
	RAVE_OBJECT_RELEASE(attr);
	RAVE_OBJECT_RELEASE(qfield);

	return ret;
}


int verticalTexture(PolarVolume_t* pvol, PolarScan_t* etop, RaveField_t* vtfield, const char* paramname) {
	PolarScanParam_t* maxRField = RAVE_OBJECT_NEW(&PolarScanParam_TYPE);
	PolarScanParam_t* maxRHeightField = RAVE_OBJECT_NEW(&PolarScanParam_TYPE);
	PolarScanParam_t* ETOP = NULL;
	RaveValueType rvt_z, rvt_etop;
	double hght, dbz, bind, binh, offset;
	int nscans, nrays, nbins, s, r, b, zbins;
	int bu = 1;  /* default assumption is a bottom-up pvol */
	int ret = 1;

	ETOP = PolarScan_getParameter(etop, "HGHT");

	nscans = PolarVolume_getNumberOfScans(pvol);
	nrays = PolarScan_getNrays(etop);
	nbins = PolarScan_getNbins(etop);

	PolarScanParam_createData(maxRField, nbins, nrays, RaveDataType_DOUBLE);
	PolarScanParam_createData(maxRHeightField, nbins, nrays, RaveDataType_DOUBLE);
	PolarScanParam_setQuantity(maxRField, "MAXR");
	PolarScanParam_setQuantity(maxRHeightField, "MAXRH");

	/* Bottom-up check */
	bu = PolarVolume_isAscendingScans(pvol);
	if (!bu) {
		PolarVolume_sortByElevations(pvol, 1);
	}

	/* For each ray and bin, loop in vertical starting at bottom, up to echo-top height */
	for (r=0; r<nrays; r++) {
		for (b=0; b<nbins; b++) {
			double *list = RAVE_MALLOC(nscans * sizeof(double));
			int n = 0;
			double sum = 0.0;

			for (s=0; s<nscans; s++) {
				PolarScan_t* scan = NULL;
				PolarScanParam_t* param = NULL;
				PolarNavigator_t* pnav = NULL;
				scan = PolarVolume_getScan(pvol, s);
				param = PolarScan_getParameter(scan, paramname);
				pnav = PolarScan_getNavigator(scan);
				double rscale = PolarScan_getRscale(scan);
				double elangle = PolarScan_getElangle(scan);
				double maxR;
				zbins = PolarScan_getNbins(scan);
				offset = PolarScanParam_getOffset(param);
				if (s == 0) {  /* Initialize */
					PolarScanParam_setValue(maxRField, b, r, 0.0);
					PolarScanParam_setValue(maxRHeightField, b, r, 0.0);
				}
				if (b > zbins) {  /* In-bounds check */
					RAVE_OBJECT_RELEASE(scan);
					RAVE_OBJECT_RELEASE(param);
					RAVE_OBJECT_RELEASE(pnav);
					continue;
				}
				PolarNavigator_reToDh(pnav, b*rscale, elangle, &bind, &binh);  /* distance and height from range and azimuth */
				rvt_etop = PolarScanParam_getConvertedValue(ETOP, b, r, &hght);  /* ETOP should already be median-filtered */
				if (binh > (hght*1000+100)) {  /* If this echo is above the echo-top + buffer, then break */
					RAVE_OBJECT_RELEASE(scan);
					RAVE_OBJECT_RELEASE(param);
					RAVE_OBJECT_RELEASE(pnav);
					continue;
				}

				rvt_z = PolarScanParam_getConvertedValue(param, b, r, &dbz);
				if (rvt_z == RaveValueType_UNDETECT) {
					dbz = offset;  /* should be -32 */
				}
				if (rvt_z != RaveValueType_NODATA) {
					list[s] = dbz;
					sum += dbz;
					n += 1;

					PolarScanParam_getValue(maxRField, b, r, &maxR);
					if (dbz > maxR) {
						PolarScanParam_setValue(maxRField, b, r, dbz);
						PolarScanParam_setValue(maxRHeightField, b, r, binh/1000.0);
					}

				}
				RAVE_OBJECT_RELEASE(scan);
				RAVE_OBJECT_RELEASE(param);
				RAVE_OBJECT_RELEASE(pnav);
			}
			if (n > 1) {
				double mean = sum / n;
				double ssum = 0.0;
				double std = 0.0;

				for (s=0; s<n; s++) {
					ssum += pow(list[s] - mean, 2);
				}
				std = sqrt(ssum / (n-1));
				ret = RaveField_setValue(vtfield, b, r, std);
			}

			RAVE_FREE(list);
		}
	}
	ret = 0;

	ret = addStringAttribute(vtfield, "how/task", "ca.ec.characterize.vertical_texture");
	PolarScan_addParameter(etop, maxRField);
	PolarScan_addParameter(etop, maxRHeightField);
	/* Bottom-up check again, to set things right */
	if (!bu) {
		PolarVolume_sortByElevations(pvol, 0);
	}

	RAVE_OBJECT_RELEASE(ETOP);
	return ret;
}


int echotopMedian(PolarScan_t* etop, int raypad, int binpad) {
	PolarScanParam_t* ETOP = NULL;
	PolarScanParam_t* ETOPC = NULL;  /* To clone etop */
	RaveValueType rvt_etop;
	double hght, median, gain, offset;
	int ret = 1;
	int nrays, nbins, r, b, lr, lb, tr;

	if (PolarScan_hasParameter(etop, "HGHT")) {
		ETOP = PolarScan_getParameter(etop, "HGHT");
	} else {
		RAVE_ERROR0("Echo-top median filter: Input echotop scan contains no echo tops called HGHT. Bailing ...");
		return 0;
	}

	gain = PolarScanParam_getGain(ETOP);
	offset = PolarScanParam_getOffset(ETOP);
	ETOPC = RAVE_OBJECT_CLONE(ETOP);
	if (ETOPC == NULL) {
		ret = 0;
		goto done;
	}

	nrays = PolarScan_getNrays(etop);
	nbins = PolarScan_getNbins(etop);
	for (r=0; r<nrays; r++) {
		for (b=0; b<nbins; b++) {
			double sum = 0.0;
			int n = 0;
			int maxn = 2*(raypad+1) * 2*(binpad+1);
			double *list = RAVE_MALLOC(maxn * sizeof(double));

			for (lr=r-raypad ; lr<=r+raypad ; lr++) {
				if (lr < 0) {
					tr = (nrays-1) + lr;
				} else if (lr >= nrays) {
					tr = lr - nrays;
				} else tr = lr;

				for (lb=b-binpad ; lb<=b+binpad ; lb++) {
					/* In-range while in loop check */
					if ( (lb >= 0) && (lb < nbins) ) {
						rvt_etop = PolarScanParam_getConvertedValue(ETOP, lb, tr, &hght);

						if (rvt_etop == RaveValueType_DATA) {
							sum += hght;
							list[n] = hght;
							n += 1;
						}
					}
				}
			}
			if (n > 0) {
				double temp;
				int i, j;

				for(i = 0; i < n; ++i){    /* median */
					for(j = i + 1; j < n; ++j){
						if(list[i] > list[j]){
							temp = list[i];
							list[i] = list[j];
				            list[j] = temp;
						}
					}
				}
				if(n % 2 == 0) median = (list[n / 2] + list[n / 2 + 1]) / 2;
				else median = list[n / 2 + 1];

				median = (median - offset) / gain; /* scale because there is no _setConvertedValue function */
				PolarScanParam_setValue(ETOPC, b, r, median);
			}
			RAVE_FREE(list);
		}
	}

	/* Would prefer to just copy over the data. Why do I have to loop? */
	for (r=0; r<nrays; r++) {
		for (b=0; b<nbins; b++) {
			rvt_etop = PolarScanParam_getValue(ETOPC, b, r, &hght);
			PolarScanParam_setValue(ETOP, b, r, hght);
		}
	}
	RAVE_OBJECT_RELEASE(ETOPC);
done:
	RAVE_OBJECT_RELEASE(ETOP);
	return ret;
}


int echotopFilter(PolarScan_t* zscan, PolarScan_t* etop, double zthresh, double hthresh, const char* paramname) {
	PolarScanParam_t* ZPARAM = NULL;
	PolarScanParam_t* ETOP = NULL;
	RaveField_t* qfield = NULL;
	RaveValueType rvt_z, rvt_etop;
	PolarNavigationInfo navinfo;
	int ret=1;
	int znrays, znbins, r, b;
	double zgain, zoffset, znodata, zundetect, lat, lon, dbz, hght, dbzhght;
	double pet_a = 0.25;  // Precip-ET coefficient a = 1/4
	double pet_z0 = 23.0; // Precip-ET reflectivity z0 = 23 dBZ
	double pet_h0 = 2.35; // Precip-ET lowest echo-top = 2.35 km
	const char* qidentifier = "ca.ec.filter.echotop";
	initNavinfo(&navinfo);   /* shut up the compiler */

	if ( (strcmp(paramname, "TH")) && (strcmp(paramname, "DBZH")) ) {
		RAVE_ERROR0("Echo-top filter: Input parameter not TH or DBZH. Bailing ...");
	}
	if (PolarScan_hasParameter(zscan, paramname)) {
		ZPARAM = PolarScan_getParameter(zscan, paramname);
	} else {
		RAVE_ERROR1("Echo-top filter: Input scan contains no reflectivity quantity called %s. Bailing ...", paramname);
		return 0;
	}
	if (PolarScan_hasParameter(etop, "HGHT")) {
		ETOP = PolarScan_getParameter(etop, "HGHT");
	} else {
		RAVE_ERROR0("Echo-top filter: Input echotop scan contains no echo tops called HGHT. Bailing ...");
		ret = 0;
		goto done;
	}

	/* This QC has already been performed if the QC attribute exists, so don't redo it */
	qfield = PolarScan_getQualityFieldByHowTask(zscan, qidentifier);
	if (qfield) {
		RAVE_ERROR0("Echo-top filtering has already been performed. Will not be redone.");
		ret = 0;
		goto done;
	} else {
		qfield = RAVE_OBJECT_NEW(&RaveField_TYPE);
	}

	znrays = PolarScan_getNrays(zscan);
	znbins = PolarScan_getNbins(zscan);
	zgain = PolarScanParam_getGain(ZPARAM);
	zoffset = PolarScanParam_getOffset(ZPARAM);
	znodata = PolarScanParam_getNodata(ZPARAM);
	zundetect = PolarScanParam_getUndetect(ZPARAM);

	RaveField_createData(qfield, (long)znbins, (long)znrays, RaveDataType_UCHAR);
	addDoubleAttribute(qfield, "what/gain", zgain);
	addDoubleAttribute(qfield, "what/offset", zoffset);
	addDoubleAttribute(qfield, "what/nodata", znodata);
	addDoubleAttribute(qfield, "what/undetect", zundetect);
	addStringAttribute(qfield, "how/task", qidentifier);

	for (r=0; r<znrays; r++) {
		for (b=0; b<znbins; b++) {

			/* Initialize qfield to 1, which is scaled to 255 */
			RaveField_setValue(qfield, b, r, zundetect);

			rvt_z =  PolarScanParam_getConvertedValue(ZPARAM, b, r, &dbz);
			if (rvt_z == RaveValueType_DATA) {
				PolarScan_getLonLatFromIndex(zscan, b, r, &lon, &lat);

				/* Determine our position in the echo-top field */
				rvt_etop = PolarScan_getNearestConvertedParameterValue(etop, "HGHT", lon, lat, &hght, &navinfo);

				/* Out-of-bounds check */
				if ( (navinfo.ai == -1) || (navinfo.ri == -1) ) continue;

				/* Otherwise */
				dbzhght = (dbz-pet_z0) * pet_a;
				if (dbzhght < pet_h0) dbzhght = pet_h0;  /* Norman's horizontal line? */
				if (dbzhght >= hght) {  /* If the ET is lower than the minimum expected for that reflectivity, reject  */
					PolarScanParam_setValue(ZPARAM, b, r, zundetect);
					RaveField_setValue(qfield, b, r, (dbz - zoffset) / zgain);
				}
			}
		}
	}

	PolarScan_addQualityField(zscan, qfield);
done:
	RAVE_OBJECT_RELEASE(ZPARAM);
	RAVE_OBJECT_RELEASE(ETOP);
	RAVE_OBJECT_RELEASE(qfield);

	return ret;
}
