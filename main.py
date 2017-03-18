# -*- coding: utf-8 -*-
"""CatAtom2Osm command line entry point"""
from optparse import OptionParser
import logging

import setup
from catatom2osm import (CatAtom2Osm, ZipCodeError, LayerIOError)

log = logging.getLogger(setup.app_name)
fh = logging.FileHandler(setup.log_file)
ch = logging.StreamHandler()
fh.setLevel(logging.DEBUG)
fh.setLevel(logging.INFO)
formatter = logging.Formatter(setup.log_format)
ch.setFormatter(formatter)
fh.setFormatter(formatter)
log.addHandler(ch)
log.addHandler(fh)

usage = """%prog <path>
The argument path states the directory where the source files are located.
The directory name shall start with 5 digits (GGMMM) matching the Cadastral
Provincial Office and Municipality Code."""
    

if __name__ == "__main__":
    parser = OptionParser(usage=usage)
    parser.add_option("", "--log", dest="log_level", metavar="log_level",
        default=setup.log_level, help="Select the log level between " +
        "DEBUG, INFO, WARNING, ERROR or CRITICAL.")
    parser.add_option("-a", "--address", dest="address", default=False,
        action="store_true", help="Process the address dataset.")
    parser.add_option("-p", "--parcel", dest="parcel", default=False,
        action="store_true", help="Process the cadastral parcel dataset.")
    parser.add_option("-z", "--zoning", dest="zoning", default=False,
        action="store_true", help="Process the cadastral zoning dataset.")
    (options, args) = parser.parse_args()
    log_level = getattr(logging, options.log_level.upper(), None)
    if log_level == None:
        log.error('Invalid log level: %s' % options.log_level)
    log.setLevel(log_level)

    if len(args) < 1:
        parser.print_help()
    elif len(args) > 1:
        log.error("Too many arguments, supply only a directory path.")
    else:
        try:
            app = CatAtom2Osm(args[0], options)
            app.run()
            del app
        except (IOError, ZipCodeError, LayerIOError) as e:
            log.error(e)

