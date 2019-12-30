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
/**
 * Python wrapper to RAVE's EC extensions
 * @file
 * @author Daniel Michelson, Environment and Climate Change Canada
 * @date 2016-06-02
 */
#include "Python.h"
#include "arrayobject.h"
#include "rave.h"
#include "rave_debug.h"
#include "pyrave_debug.h"
#include "pypolarvolume.h"
#include "pypolarscan.h"
#include "pyravefield.h"
#include "raveec.h"

/**
 * Debug this module
 */
PYRAVE_DEBUG_MODULE("_rave_ec");

/**
 * Sets a Python exception.
 */
#define Raise(type,msg) {PyErr_SetString(type,msg);}

/**
 * Sets a Python exception and goto tag
 */
#define raiseException_gotoTag(tag, type, msg) \
{PyErr_SetString(type, msg); goto tag;}

/**
 * Sets a Python exception and return NULL
 */
#define raiseException_returnNULL(type, msg) \
{PyErr_SetString(type, msg); return NULL;}

/**
 * Error object for reporting errors to the Python interpreter
 */
static PyObject *ErrorObject;


/**
 * Runs the DOPVOL filter
 * @param[in] PolarScan_t object, hopefully containing a "DBZH" parameter
 * @param[in] PolarScan_t object, hopefully containing a "VRADH" parameter
 * @returns Py_True (success) or Py_False (failure)
 */
static PyObject* _dopvolFilter_func(PyObject* self, PyObject* args) {
  PyObject* convolobj = NULL;
  PyObject* dopvolobj = NULL;
  PyPolarScan* pyconvol = NULL;
  PyPolarScan* pydopvol = NULL;
  int spatial = 0;

  if (!PyArg_ParseTuple(args, "OOi", &convolobj, &dopvolobj, &spatial)) {
    return NULL;
  }

  if (PyPolarScan_Check(convolobj)) {
    pyconvol = (PyPolarScan*)convolobj;
  } else {
    raiseException_returnNULL(PyExc_AttributeError, "DOPVOL filter requires CONVOL scan as input");
  }
  if (PyPolarScan_Check(dopvolobj)) {
    pydopvol = (PyPolarScan*)dopvolobj;
  } else {
    raiseException_returnNULL(PyExc_AttributeError, "DOPVOL filter requires DOPVOL scan as input");
  }

  if (dopvolFilter(pyconvol->scan, pydopvol->scan, spatial)) {
    return PyBool_FromLong(1); /* Instead of Py_RETURN_TRUE since compiler screams about dereferencing */
  }
  return PyBool_FromLong(0); /* Instead of Py_RETURN_FALSE since compiler screams about dereferencing */
}


/**
 * Calculates standard deviation of reflectivity in the vertical as a measure of texture.
 * Relies on a pre-initiated field for storing the per-bin texture.
 * @param[in] PolarVolume_t object - input (CONVOL) polar volume containing reflectivity
 * @param[in] PolarScan_t object - input scan containing echo-top info, used to constrain the calculations
 * @param[in] RaveField_t - field object that will be populated with standard deviation
 * @param[in] const char - string of the reflectivity quantity to process: TH or DBZH
 * @return int 1 if successful, otherwise 0
 */
static PyObject* _verticalTexture_func(PyObject* self, PyObject* args) {
	PyObject* pvolobj = NULL;
	PyObject* etopobj = NULL;
	PyObject* fieldobj = NULL;
	PyPolarVolume* pypvol = NULL;
	PyPolarScan* pyetop = NULL;
	PyRaveField* pyfield = NULL;
	const char* paramname;

	if (!PyArg_ParseTuple(args, "OOOs", &pvolobj, &etopobj, &fieldobj, &paramname)) {
		return NULL;
	}

	if (PyPolarVolume_Check(pvolobj)) {
		pypvol = (PyPolarVolume*)pvolobj;
	} else {
		raiseException_returnNULL(PyExc_AttributeError, "Vertical texture requires polar volume as input");
	}
	if (PyPolarScan_Check(etopobj)) {
		pyetop = (PyPolarScan*)etopobj;
	} else {
		raiseException_returnNULL(PyExc_AttributeError, "Vertical texture requires echo-top scan as input");
	}
	if (PyRaveField_Check(fieldobj)) {
		pyfield = (PyRaveField*)fieldobj;
	} else {
		raiseException_returnNULL(PyExc_AttributeError, "Vertical texture requires initialized RaveField as input");
	}

	if (verticalTexture(pypvol->pvol, pyetop->scan, pyfield->field, paramname)) {
		return PyBool_FromLong(1); /* Instead of Py_RETURN_TRUE since compiler screams about dereferencing */
	}
	return PyBool_FromLong(0); /* Instead of Py_RETURN_FALSE since compiler screams about dereferencing */
}


/**
 * Median filters an echo-top field
 * @param[in] PolarScan_t object, containing a "HGHT" parameter
 * @param[in] int how much azimuthal one-way padding in the filtering kernel
 * @param[in] int how much one-way padding in range in the filtering kernel
 * @returns Py_True (success) or Py_False (failure)
 */
static PyObject* _echotopMedian_func(PyObject* self, PyObject* args) {
	PyObject* etopobj = NULL;
	PyPolarScan* pyetopscan = NULL;
	int raypad, binpad;

	if (!PyArg_ParseTuple(args, "Oii", &etopobj, &raypad, &binpad)) {
		return NULL;
	}

	if (PyPolarScan_Check(etopobj)) {
		pyetopscan = (PyPolarScan*)etopobj;
	} else {
		raiseException_returnNULL(PyExc_AttributeError, "Echo-top median filter requires echo-top scan as input");
	}

	if (echotopMedian(pyetopscan->scan, raypad, binpad)) {
		return PyBool_FromLong(1); /* Instead of Py_RETURN_TRUE since compiler screams about dereferencing */
	}
	return PyBool_FromLong(0); /* Instead of Py_RETURN_FALSE since compiler screams about dereferencing */
}


/**
 * Runs the Echo-top filter
 * @param[in] PolarScan_t object, hopefully containing a "DBZH" or "TH" parameter
 * @param[in] PolarScan_t object, hopefully containing a "HGHT" parameter
 * @param[in] double reflectivity threshold value
 * @param[in] double echo-top threshold value
 * @param[in] string representing reflectivity quantity, either "DBZH" or "TH"
 * @returns Py_True (success) or Py_False (failure)
  */
static PyObject* _echotopFilter_func(PyObject* self, PyObject* args) {
  PyObject* zscanobj = NULL;
  PyObject* etopobj = NULL;
  PyPolarScan* pyzscan = NULL;
  PyPolarScan* pyetopscan = NULL;
  double zthresh, ethresh;
  const char* paramname;

  if (!PyArg_ParseTuple(args, "OOdds", &zscanobj, &etopobj, &zthresh, &ethresh, &paramname)) {
    return NULL;
  }

  if (PyPolarScan_Check(zscanobj)) {
    pyzscan = (PyPolarScan*)zscanobj;
  } else {
    raiseException_returnNULL(PyExc_AttributeError, "Echo-top filter requires reflectivity scan as input");
  }
  if (PyPolarScan_Check(etopobj)) {
    pyetopscan = (PyPolarScan*)etopobj;
  } else {
    raiseException_returnNULL(PyExc_AttributeError, "Echo-top filter requires echo-top scan as input");
  }

  if (echotopFilter(pyzscan->scan, pyetopscan->scan, zthresh, ethresh, paramname)) {
    return PyBool_FromLong(1); /* Instead of Py_RETURN_TRUE since compiler screams about dereferencing */
  }
  return PyBool_FromLong(0); /* Instead of Py_RETURN_FALSE since compiler screams about dereferencing */
}


static struct PyMethodDef _raveec_functions[] =
{
  { "dopvolFilter", (PyCFunction) _dopvolFilter_func, METH_VARARGS },
  { "verticalTexture", (PyCFunction) _verticalTexture_func, METH_VARARGS },
  { "echotopMedian", (PyCFunction) _echotopMedian_func, METH_VARARGS },
  { "echotopFilter", (PyCFunction) _echotopFilter_func, METH_VARARGS },
  { NULL, NULL }
};

/**
 * Initialize the _rave_ec module
 */
PyMODINIT_FUNC init_rave_ec(void)
{
  PyObject* m;
  m = Py_InitModule("_rave_ec", _raveec_functions);
  ErrorObject = PyString_FromString("_rave_ec.error");

  if (ErrorObject == NULL || PyDict_SetItemString(PyModule_GetDict(m),
                                                  "error", ErrorObject) != 0) {
    Py_FatalError("Can't define _rave_ec.error");
  }
  import_pypolarvolume();
  import_pypolarscan();
  import_pyravefield();
  import_array(); /*To make sure I get access to numpy*/
  PYRAVE_DEBUG_INITIALIZE;
}

/*@} End of Module setup */
