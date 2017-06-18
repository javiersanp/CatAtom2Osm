# -*- coding: utf-8 -*-
"""OSM XML format serializer"""

# See http://lxml.de/tutorial.html for the source of the includes
import setup
import logging
log = logging.getLogger(setup.app_name + "." + __name__)

try:
    from lxml import etree
    log.debug(_("Running with lxml.etree"))
except ImportError:
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
    for node in data.nodes:
        attrs = dict(id=str(node.id), action=node.action, visible=node.visible)
        attrs.update(dict(lat=str(node.y), lon=str(node.x)))
        nodexml = etree.Element('node', attrs)
        for key, value in node.tags.items():
            nodexml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(nodexml)
    for way in data.ways:
        attrs = dict(id=str(way.id), action=way.action, visible=way.visible)
        wayxml = etree.Element('way', attrs)
        for node in way.nodes:
            wayxml.append(etree.Element('nd', dict(ref=str(node.id))))
        for key, value in way.tags.items():
            wayxml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(wayxml)
    for rel in data.relations:
        attrs = dict(id=str(rel.id), action=rel.action, visible=rel.visible)
        relxml = etree.Element('relation', attrs)
        for m in rel.members:
            attrs = dict(type=m.type, ref=str(m.ref), role=m.role)
            relxml.append(etree.Element('member', attrs))
        for key, value in rel.tags.items():
            relxml.append(etree.Element('tag', dict(k=key, v=value)))
        root.append(relxml)
    try:
        result = etree.tostring(root, pretty_print=True)
    except TypeError:
        result = etree.tostring(root)
    return result
    
