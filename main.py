# -*- coding: utf-8 -*-
"""CatAtom2Osm command line entry point"""
from optparse import OptionParser
import logging
import gettext
import sys
import os
from zipfile import BadZipfile
import setup

if setup.platform.startswith('win'):
    if os.getenv('LANG') is None:
        os.environ['LANG'] = setup.language
gettext.install(setup.app_name.lower(), localedir=setup.localedir, unicode=1)
 
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

def run():
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--version", dest="version", default=False,
        action="store_true", help=_("Print CatAtom2Osm version and exit"))
    parser.add_option("-l", "--list", dest="list", metavar="prov",
        default=False, help=_("List available municipalities given the two "
        "digits province code"))
    parser.add_option("-t", "--tasks", dest="tasks", default=False,
        action="store_true", help=_("Splits constructions into tasks files " \
        "(default, implies -z)"))
    parser.add_option("-z", "--zoning", dest="zoning", default=False,
        action="store_true", help=_("Process the cadastral zoning dataset"))
    parser.add_option("-b", "--building", dest="building", default=False,
        action="store_true", help=_("Process constructions to a single file " \
        "instead of tasks"))
    parser.add_option("-d", "--address", dest="address", default=False,
        action="store_true", help=_("Process the address dataset"))
    parser.add_option("-p", "--parcel", dest="parcel", default=False,
        action="store_true", help=_("Process the cadastral parcel dataset"))
    parser.add_option("-a", "--all", dest="all", default=False,
        action="store_true", help=_("Process all datasets (equivalent " \
        "to -bdptz)"))
    parser.add_option("", "--log", dest="log_level", metavar="log_level",
        default=setup.log_level, help=_("Select the log level between " \
        "DEBUG, INFO, WARNING, ERROR or CRITICAL."))
    (options, args) = parser.parse_args()
    if options.all:
        options.building = True
        options.tasks = True
        options.address = True
        options.parcel = True
    if not (options.tasks or options.zoning or options.building or 
            options.address or options.parcel):
        options.tasks = True
    if options.tasks:
        options.zoning = True
    log_level = getattr(logging, options.log_level.upper(), None)
    if log_level == None:
        log.error(_('Invalid log level: %s') % options.log_level)
    else:
        log.setLevel(log_level)

    if options.version:
        print _("%s version %s") % (setup.app_name, setup.app_version)
    elif len(args) > 1:
        log.error(_("Too many arguments, supply only a directory path."))
    elif len(args) < 1 and not options.list:
        parser.print_help()
    else:
        from catatom import list_municipalities
        try:
            if options.list:
                list_municipalities(options.list)
            else:
                from catatom2osm import CatAtom2Osm
                app = CatAtom2Osm(args[0], options)
                app.run()
                app.exit()
        except (ImportError, IOError, OSError, ValueError, BadZipfile) as e:
            log.error(e.message)
            if 'qgis' in e.message or 'core' in e.message or 'osgeo' in e.message:
                log.error(_("Please, install QGIS"))

if __name__ == "__main__":
    run()
