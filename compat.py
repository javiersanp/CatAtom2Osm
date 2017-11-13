import sys
import logging
import setup

log = logging.getLogger(setup.app_name + "." + __name__)

log.debug(_("Using Python %s.%s.%s"), *sys.version_info[:3])

# See http://lxml.de/tutorial.html for the source of the includes
try:
    from lxml import etree
    log.debug(_("Running with lxml.etree"))
except ImportError: # pragma: no cover
    try:
        import xml.etree.ElementTree as etree
        log.debug(_("Running with ElementTree on Python 2.5+"))
    except ImportError:
        try:
            import cElementTree as etree
            log.debug(_("Running with cElementTree"))
        except ImportError:
            try:
                import elementtree.ElementTree as etree
                log.debug(_("Running with ElementTree"))
            except ImportError:
                msg = _("Failed to import ElementTree from any known place")
                raise ImportError(msg)

