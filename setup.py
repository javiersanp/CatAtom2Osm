# -*- coding: utf-8 -*-
app_name = 'CatAtom2Osm'
app_version = '2017-03-22'
app_author = u'Javier Sánchez Portero'
app_copyright = u'2017, Javier Sánchez Portero'

"""Application preferences"""
log_level = 'INFO' # Default console log level
log_file = 'catatom2osm.log'
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

qgs_prefix_path = '/usr' # qGis API prefix path. TODO: detect OS
fn_prefix = 'A.ES.SDGC' # Inspire Atom file name prefix

silence_gdal = False

dup_thr = 0.01 # Distance in meters to merge nearest vertexs.
dist_thr = 0.05 # Threshold in meters for vertex simplification and topological points.
angle_thr = 2 # Threshold in degrees from straight angle to delete a vertex
