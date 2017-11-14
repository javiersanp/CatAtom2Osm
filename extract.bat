@echo off
if "%1"=="" (

  echo Uso: %0 PATH

  goto END

)
set OUTPATH=%1


if not exist "%1\*.pbf" (
    echo PATH debe contener un fichero .pbf

    goto END
)
for /f "delims=" %%F in ('dir %OUTPATH%\*.pbf /b') do set PBFFILE="%OUTPATH%\%%F"

set POLYGON="%OUTPATH%\boundary.poly"

if not exist %POLYGON% (

    echo PATH debe contener un fichero boundary.poly

    goto END
)


set CURADDR="%OUTPATH%\current_address.osm"

if not exist %CURADDR% call osmosis ^
    --read-pbf %PBFFILE% ^
    --node-key keyList="addr:street,addr:place" ^
    --tag-filter accept-nodes "addr:housenumber=*" outPipe.0=nodedata ^
    ^
    --read-pbf %PBFFILE% ^
    --way-key keyList="addr:street,addr:place" ^
    --tf reject-relations --used-node outPipe.0=waydata ^
    --tf reject-relations --used-node outPipe.0=waydata ^
    ^
    --merge inPipe.0=nodedata inPipe.1=waydata outPipe.0=waynodedata ^
    ^
    --read-pbf %PBFFILE% ^
    --tag-filter accept-relations "addr:street=*" "addr:plac=*" ^
    --tag-filter accept-relations "addr:housenumber=*" ^
    --used-way --used-node outPipe.0=reldata ^
    ^
    --merge inPipe.0=waynodedata inPipe.1=reldata ^
    --write-xml %CURADDR%


set CURHGW="%OUTPATH%\current_highway.osm"

if not exist %CURHGW% call osmosis ^
    --read-pbf %PBFFILE% ^
    --node-key-value keyValueList="place.square" outPipe.0=nodedata ^
    ^
    --read-pbf %PBFFILE% ^
    --tag-filter accept-ways "highway=*" "place=square" ^
    --tag-filter accept-ways "name=*" ^
    --tf reject-relations --used-node outPipe.0=waydata ^
    ^
    --merge inPipe.0=nodedata inPipe.1=waydata outPipe.0=waynodedata ^
    ^
    --read-pbf %PBFFILE% ^
    --tag-filter accept-relations "place=square" ^
    --tag-filter accept-relations "name=*" ^
    --used-way --used-node outPipe.0=reldata ^
    ^
    --merge inPipe.0=waynodedata inPipe.1=reldata ^
    --bounding-polygon file=%POLYGON% ^
    --write-xml %CURHGW%


set CURBU="%OUTPATH%\current_building.osm"

if not exist %CURBU% call osmosis ^
    --read-pbf %PBFFILE% ^
    --tag-filter accept-ways "building=*" "leisure=swimming_pool" ^
    --tf reject-relations --used-node outPipe.0=waydata ^
    ^
    --read-pbf %PBFFILE% ^
    --tag-filter accept-relations "building=*" "leisure=swimming_pool" ^
    --used-way --used-node outPipe.0=reldata ^
    ^
    --merge inPipe.0=waydata inPipe.1=reldata ^
    --bounding-polygon file=%POLYGON% ^
    --write-xml %CURBU%

dir "%OUTPATH%\current_*.osm"

:END
