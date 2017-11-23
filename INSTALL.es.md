Instalación
===========

Linux
-----

En una consola de comandos ejecutar::

    sudo apt install qgis git pip
    cd ~
    mkdir catastro
    cd catastro
    git clone https://github.com/javiersanp/CatAtom2Osm.git
    cd CatAtom2Osm
    sudo pip install -r requisites.txt
    sudo make install

Si se desea instalar el entorno de pruebas::

    sudo pip install -r requisites-dev.txt
    
Y para ejecutar las pruebas del código::

    make test
    
Se sugiere ejecutar el programa en la carpeta ~/catastro

Mac OS X
--------

Instalar QGIS desde la página de descarga de KyngChaos 
http://www.kyngchaos.com/software/qgis

Instalar el programa de escritorio de GitHub desde
http://desktop.github.com

Ejecutarlo y descargar el repositorio 
https://github.com/javiersanp/CatAtom2Osm.git

Abrir una consola de comandos y cambiar a la carpeta CatAtom2Osm descargada
anteriormente. Ejecutar los comandos::

    sudo easy_install pip
    sudo pip install -r requisites.txt
    sudo make install

Durante la instalación de los requisitos pedirá la instalación de las 
herramientas para desarrolladores de la línea de comandos.

Si se desea instalar el entorno de pruebas::

    sudo pip install -r requisites-dev.txt
    
Y para ejecutar las pruebas del código::

    make test

Windows
-------

Instalar QGIS usando el instalador OSGeo4W en red (64 bits/ 32 bits) desde la
página de descarga de http://qgis.org

* Ejecutar el instalador y seleccionar la opción Instalación Avanzada
* Instalar desde Internet
* Como directorio de instalación usar C:\OSGeo4W
* Seleccionar las opciones por defecto
* En la pantalla de selección de paquetes seleccionar:

  * Desktop -> qgis: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python-devel
  * Libs -> python-pip
  * Libs -> setuptools

* Aceptar la lista de dependencias sugerida

Instalar Microsoft Visual C++ Compiler for Python 2.7 desde 
http://aka.ms/vcpython27

Descargar el paquete python-levenshtein en las librerías no oficiales de 
Christoph Gohlke desde http://www.lfd.uci.edu/~gohlke/Pythonlibs/

Instalar el programa de escritorio de GitHub desde desktop.github.com

Ejecutarlo y descargar el repositorio https://github.com/javiersanp/CatAtom2Osm.git

En la carpeta CatAtom2Osm descargada lanzar el archivo pyqgis.bat. 
En la consola resultante ejecutar::

    python -m pip install -r requisites.txt
    python -m pip install ruta al archivo descargado/python_Levenshtein‑0.12.0‑cp27‑cp27m‑win_amd64.whl

Si se desea instalar el entorno de pruebas::

    python -m pip install -r requisites-dev.txt
    
Y para ejecutar las pruebas del código::

    python -m unittest discover

Será necesario ejecutar pyqgis.bat cuando queramos usar el programa para abrir una consola de comandos con el entorno de Python QGIS adecuado. Se sugiere editar el archivo pyqgis.bat, descomentar la penúltima línea con la orden CD e introducir la ruta de la carpeta donde se van a descargar los archivos de Catastro. Por ejemplo::

    cd c:\Users\Javier\Documents\catastro
