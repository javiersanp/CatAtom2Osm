"""Entry point to run test with coverage.py"""

# copied directly from 2.7's unittest/__main__.py b/c coverage can't do -m

from qgis.core import QgsApplication
import gdal


class QgsSingleton(QgsApplication):
    _qgs = None
    
    def __new__(cls):
        if QgsSingleton._qgs is None:
            QgsSingleton._qgs = QgsApplication([], False)
            QgsSingleton._qgs.initQgis()
            gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
            gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        return QgsSingleton._qgs
    

if __name__ == "__main__":
    import sys
    if sys.argv[0].endswith("__main__.py"):
        sys.argv[0] = "python -m unittest"

    __unittest = True

    from unittest.main import main, TestProgram, USAGE_AS_MAIN
    TestProgram.USAGE = USAGE_AS_MAIN 
    main(module=None)

