Read me
=======

Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services (http://www.catastro.minhap.gob.es/webinspire/index.html) to OSM files.

Requeriments
------------

* pyqgis
* GDAL

Instalation
-----------

Everything we need can be installed using the installers available on the QGIS 
website. http://qgis.org/

The code has been tested in Ubuntu 16.04.2, QGIS 2.8.6wien, python 2.7.12. 

Usage
-----

To run the application:

    python main.py <path>

The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre.

**Options**:

* \-h, --help        Show this help message and exit
* \--log=log_level   Select the log level between DEBUG, INFO, WARNING, ERROR or 
  CRITICAL.
* \-a, --address     Process the address dataset.
* \-p, --parcel      Process the Cadastral parcel dataset.
* \-z, --zoning      Process the Cadastral zoning dataset.

Documentation
-------------

Browse the software documentation.

https://javiersanp.github.io/CatAtom2Osm/

