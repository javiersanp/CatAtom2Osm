Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services (http://www.catastro.minhap.gob.es/webinspire/index.html) to OSM files.

Requeriments
============

* pyqgis
* GDAL

Instalation
===========

Everything we need can be installed using the installers available on the QGIS 
website. http://qgis.org/

The code has been tested in Ubuntu 16.04.2, QGIS 2.8.6wien, python 2.7.12. 

Usage
=====

To run tests:

    python -m unittest discover

To run the application:

    python main.py <path>

The argument path states the directory where the source files are located. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code.

The directory shall contain three ZIP data files downloaded from the INSPIRE
Services of the Spanish Cadastre:

* A.ES.SDGC.CP.GGMMM.zip (Cadastral Parcels) 
* A.ES.SDGC.BU.GGMMM.zip (Buildings)
* A.ES.SDGC.AD.GGMMM.zip (Addresses)

Options:

* -h, --help: Show this help message and exit
* \--log=log_level: Select the log level between DEBUG, INFO, WARNING, ERROR or CRITICAL.

Documentation
=============

Browse the software documentation.

https://javiersanp.github.io/CatAtom2Osm/

