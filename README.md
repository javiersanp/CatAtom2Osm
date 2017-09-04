Read me
=======

Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services (http://www.catastro.minhap.gob.es/webinspire/index.html) to OSM files. This is part of an import proposal under construction:

https://wiki.openstreetmap.org/wiki/Spanish_Cadastre/Buildings_Import

Warning
-------

Only for testing purposses. Don't upload any result to OSM.

Requeriments
------------

* fuzzywuzzy[speedup]
* pyqgis
* requests
* GDAL

See INSTALL.md (https://javiersanp.github.io/CatAtom2Osm/es/install.html)

Usage
-----

To run the application:

    catatom2osm <path>

The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre.

**Options**:

* \-h, --help            Show this help message and exit
* \-v, --version         Print CatAtom2Osm version and exit
* \-l prov, --list=prov  List available municipalities given the two digits province code
* \-t, --tasks           Splits constructions into tasks files (default, implies -z)
* \-T, --tasklm          The same as -t but with lower memory consumption
* \-z, --zoning          Process the cadastral zoning dataset.
* \-b, --building        Process constructions to a single file instead of tasks
* \-d, --address         Process the address dataset
* \-p, --parcel          Process the cadastral parcel dataset
* \-a, --all             Process all datasets (equivalent to -dptz)
* \-m, --manual          Dissable conflation of buildings and addresses
* \--log=log_level       Select the log level between DEBUG, INFO, WARNING, ERROR or CRITICAL

Documentation
-------------

Browse the software documentation.

https://javiersanp.github.io/CatAtom2Osm/en

