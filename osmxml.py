# -*- coding: utf-8 -*-
"""OSM XML format serializer"""

import setup
import logging
import osm
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
    root = etree.Element('osm', data.attrs)
    if data.note is not None:
        nxml = etree.Element('note')
        nxml.text = data.note
        root.append(nxml)
    if data.meta is not None:
        mxml = etree.Element('meta')
        for (k, v) in data.meta.items():
            mxml.set(k, v)
        root.append(mxml)
    if data.tags:
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

def deserialize(root, data=None):
    """Generates or append to an OSM data set from OSM XML"""
    if data is None:
        data = osm.Osm()
    data.upload = root.get('upload')
    data.version = root.get('version')
    data.generator = root.get('generator')
    note = root.find('note')
    if note is not None: data.note = note.text
    meta = root.find('meta')
    if meta is not None: data.meta = meta.attrib
    for tag in root.iterfind('changeset/tag'):
        data.tags[tag.get('k')] = tag.get('v')
    for node in root.iter('node'):
        n = data.Node(float(node.get('lon')), float(node.get('lat')), 
            attrs=dict(node.attrib))
        for t in node.iter('tag'):
            n.tags[t.get('k')] = t.get('v')
    for way in root.iter('way'):
        points = [data.get(nd.get('ref')) for nd in way.iter('nd')]
        w = data.Way(points, attrs=dict(way.attrib))
        for t in way.iter('tag'):
            w.tags[t.get('k')] = t.get('v')
    for rel in root.iter('relation'):
        r = data.Relation(attrs=dict(rel.attrib))
        for t in rel.iter('tag'):
            r.tags[t.get('k')] = t.get('v')
    for rel in root.iter('relation'):
        r = data.get(rel.get('id'), 'r')
        for m in rel.iter('member'):
            el = data.get(m.get('ref'), m.get('type'))
            r.append(el, m.get('role'))
    return data
