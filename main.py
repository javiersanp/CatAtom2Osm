# -*- coding: utf-8 -*-
"""CatAtom2Osm command line entry point"""
from optparse import OptionParser
import logging
import gettext
import sys

import setup
from catatom2osm import CatAtom2Osm

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

usage = _("""%prog <path>
The argument path states the directory for input and output files. 
The directory name shall start with 5 digits (GGMMM) matching the Cadastral 
Provincial Office and Municipality Code. If the program don't find the input 
files it will download them for you from the INSPIRE Services of the Spanish 
Cadastre.""")
   
if __name__ == "__main__":
    parser = OptionParser(usage=usage.decode('utf-8'))
    parser.add_option("", "--log", dest="log_level", metavar="log_level",
        default=setup.log_level, help=_("Select the log level between " \
        "DEBUG, INFO, WARNING, ERROR or CRITICAL."))
    parser.add_option("-a", "--address", dest="address", default=False,
        action="store_true", help=_("Process the address dataset."))
    parser.add_option("-p", "--parcel", dest="parcel", default=False,
        action="store_true", help=_("Process the cadastral parcel dataset."))
    parser.add_option("-z", "--zoning", dest="zoning", default=False,
        action="store_true", help=_("Process the cadastral zoning dataset."))
    parser.add_option("-t", "--tasks", dest="tasks", default=False,
        action="store_true", help=_("Splits results for the tasking manager."))
    (options, args) = parser.parse_args()
    if options.tasks:
        options.zoning = True
    log_level = getattr(logging, options.log_level.upper(), None)
    if log_level == None:
        log.error(_('Invalid log level: %s') % options.log_level)
    log.setLevel(log_level)

    if len(args) < 1:
        parser.print_help()
    elif len(args) > 1:
        log.error(_("Too many arguments, supply only a directory path."))
    else:
        try:
            app = CatAtom2Osm(args[0], options)
            app.run()
            del app
        except (IOError, OSError, ValueError) as e:
            log.error(e)

