Léeme
=====

Herramienta para convertir los conjuntos de datos INSPIRE de los Servicios ATOM 
del Catastro Español (http://www.catastro.minhap.gob.es/webinspire/index.html) 
a archivos OSM. Esto es parte de una propuesta de importación en construcción:

https://wiki.openstreetmap.org/wiki/Spanish_Cadastre/Buildings_Import

Advertencia
-----------

Sólo para fines de prueba. No subas ningún resultado en OSM.

Requisitos
----------

* pyqgis
* GDAL

Instalación
-----------

Todos los requisitos se pueden instalar con los instaladores disponibles en el 
sitio web de QGIS. http://qgis.org/

El código ha sido probado en Ubuntu 16.04.2, con QGIS 2.8.6wien y python 2.7.12.

Uso
---

Para ejecutar la aplicación:

    python main.py <ruta>

El argumento ruta indica el directorio para los ficheros de entrada y salida.
El nombre del directorio debe comenzar con 5 dígitos (GGMMM) correspondientes 
al Código de Oficina Provincial del Catastro y Código de Municipio. Si el 
programa no encuentra los archivos de entrada los descargará de los Servicios 
INSPIRE del Catastro Español.

**Opciones**:

* \-h, --help            Muestra este mensaje de ayuda y termina
* \-v, --version         Imprime la versión de CatAtom2Osm y termina
* \-l prov, --list=prov  Lista los municipios disponibles para el código provincial de dos dígitos
* \-t, --tasks           Reparte las construcciones en archivos de tareas (predeterminada, implica -z)
* \-z, --zoning          Procesa el conjunto de datos de zonificación catastral
* \-b, --building        Procesa las construcciones a un archivo individual en lugar de tareas
* \-d, --address         Procesa el conjunto de datos de direcciones"
* \-p, --parcel          Procesa el conjunto de datos de parcelas catastrales
* \-a, --all             Procesa todos los conjuntos de datos (equivalente a -bdptz)
* \--log=log_level       Selecciona el nivel de registro entre DEBUG, INFO, WARNING, ERROR o CRITICAL.


Documentación
-------------

Consulta la documentación del programa.

https://javiersanp.github.io/CatAtom2Osm/es

