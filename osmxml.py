# -*- coding: utf-8 -*-
"""OSM XML format serializer"""

import setup
import logging
log = logging.getLogger(setup.app_name + "." + __name__)

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
                raise ImportError(_("Failed to import ElementTree from any known place"))


def serialize(data):
    """Output XML for an OSM data set"""
    attrs = dict(upload=data.upload, version=data.version, generator=setup.app_name.lower())
    root = etree.Element('osm', attrs)
    if data.note:
        nxml = etree.Element('note')
        nxml.text = data.note
        root.append(nxml)
    if data.meta:
        mxml = etree.Element('meta')
        for (k, v) in data.meta.items():
            mxml.set(k, v)
        root.append(mxml)
    csxml = etree.Element('changeset')
    for key, value in data.tags.items():
        csxml.append(etree.Element('tag', dict(k=key, v=value)))
    root.append(csxml)
    for node in data.nodes:
        nodexml = etree.Element('node', node.attrs)
        for key, value in node.tags.items():
            nodexml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(nodexml)
    for way in data.ways:
        wayxml = etree.Element('way', way.attrs)
        for node in way.nodes:
            wayxml.append(etree.Element('nd', dict(ref=str(node.id))))
        for key, value in way.tags.items():
            wayxml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(wayxml)
    for rel in data.relations:
        relxml = etree.Element('relation', rel.attrs)
        for m in rel.members:
            relxml.append(etree.Element('member', m.attrs))
        for key, value in rel.tags.items():
            relxml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(relxml)
    try:
        result = etree.tostring(root, pretty_print=True)
    except TypeError: # pragma: no cover
        result = etree.tostring(root)
    return result
    
