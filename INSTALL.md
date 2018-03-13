Install
=======

Linux
-----

In a command line shell write:: 

    sudo apt install qgis git python-pip python-dev
    cd ~
    mkdir cadastre
    cd cadastre
    git clone https://github.com/OSM-es/CatAtom2Osm.git
    cd CatAtom2Osm
    sudo pip install -r requisites.txt
    sudo make install

After this, the program is available to run in the terminal.

    catatom2osm

It's suggested to run the code in a dedicate folder, for example.

    cd
    mkdir catastro
    cd catastro

Notes:

In Debian Jessie when you run "catatom2osm" you will get this error:
>2017-12-08 15:08:12,559 - ERROR - Required QGIS version 2.10.1 or greater

An updated version of QGIS is required, you should run::

    su
    echo 'deb     http://qgis.org/debian jessie main' > /etc/apt/sources.list.d/qgis.list
    echo 'deb-src http://qgis.org/debian jessie main' >> /etc/apt/sources.list.d/qgis.list
    apt update
    apt install qgis


Mac OS X
--------

Install QGIS from KyngChaos download page 
http://www.kyngchaos.com/software/qgis

Install GitHub desktop utility from
http://desktop.github.com

Run it and download this repository 
https://github.com/OSM-es/CatAtom2Osm.git

Open a command line shell and change the directory to the previously
downloaded CatAtom2Osm folder. Run this commands::

    sudo easy_install pip
    sudo pip install -r requisites.txt
    sudo make install

While you install the requisites you will be prompted to install the command
line developper tools, answer yes.

If necessary, edit the pyqgismac.sh file and change the locale value to the one aproppiate for your country.

After this, the program is available to run in the terminal.

    catatom2osm

It's suggested to run the code in a dedicate folder, for example.

    cd
    mkdir catastro
    cd catastro


Windows
-------

Install QGIS using the OSGeo4W Network Installer (64 bits/ 32 bits) from
http://qgis.org download page.

* Run the installe and choose the Advanced Install option.
* Install from Internet
* Enter the directory for the install C:\OSGeo4W
* Accept the default options
* From the Select packages screen select:

  * Desktop -> qgis: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python-devel
  * Libs -> python-pip
  * Libs -> setuptools

* Accept the list of unmet dependencies

Install Microsoft Visual C++ Compiler for Python 2.7 from 
http://aka.ms/vcpython27

Download the package python-levenshtein in the unofficial library of 
Christoph Gohlke from http://www.lfd.uci.edu/~gohlke/Pythonlibs/

Install the GitHub desktop utility from desktop.github.com

Run it and download the repository https://github.com/OSM-es/CatAtom2Osm.git

In the previously downloaded CatAtom2Osm folder launch the file pyqgis.bat. 
Write this in the resulting shell::

    python -m pip install -r requisites.txt
    python -m pip install path to downloaded/python_Levenshtein‑0.12.0‑cp27‑cp27m‑win_amd64.whl

To use the program it will be necessary to run pyqgis.bat to open a convenient 
Python QGIS shell. It's suggested to edit pyqgis.bat, uncomment the penultimate
line with the CD command and enter the path of the folder where you want to 
download the Cadastre files. For example::

    cd c:\Users\YourName\Documents\cadastre


Development requeriments
------------------------

Optionally, if you want to contribute to the program, install the development requeriments. In Linux and Macos:

    sudo pip install -r requisites-dev.txt
    
And to run the code tests:

    make test

In Windows::

    python -m pip install -r requisites-dev.txt
    
And to run the code tests::

    python -m unittest discover

