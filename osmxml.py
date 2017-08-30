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


def write_elem(outfile, e):
    try:
        outfile.write(etree.tostring(e, pretty_print=True))
    except TypeError: # pragma: no cover
        outfile.write(etree.tostring(e))

def serialize(outfile, data):
    """Output XML for an OSM data set"""
    outfile.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    attrs = ''.join([" {}='{}'".format(k, v) for (k,v) in data.attrs.items()])
    outfile.write("<osm{}>\n".format(attrs))
    if data.note is not None:
        e = etree.Element('note')
        e.text = data.note
        write_elem(outfile, e)
    if data.meta is not None:
        e = etree.Element('meta')
        for (k, v) in data.meta.items():
            e.set(k, v)
        write_elem(outfile, e)
    if data.tags:
        e = etree.Element('changeset')
        for (key, value) in data.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=value)))
        write_elem(outfile, e)
    for node in data.nodes:
        e = etree.Element('node', node.attrs)
        for key, value in node.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=value)))
        write_elem(outfile, e)
    for way in data.ways:
        e = etree.Element('way', way.attrs)
        for node in way.nodes:
            e.append(etree.Element('nd', dict(ref=str(node.id))))
        for key, value in way.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=value)))
        write_elem(outfile, e)
    for rel in data.relations:
        e = etree.Element('relation', rel.attrs)
        for m in rel.members:
            e.append(etree.Element('member', m.attrs))
        for key, value in rel.tags.items():
            e.append(etree.Element('tag', dict(k=key, v=value)))
        write_elem(outfile, e)
    outfile.write("</osm>\n")
        
def deserialize(infile, data=None):
    """Generates or append to an OSM data set from OSM XML"""
    if data is None:
        data = osm.Osm()
    context = etree.iterparse(infile, events=('start',))
    last_elem = data
    for event, elem in context:
        if elem.tag == 'osm':
            data.upload = elem.get('upload')
            data.version = elem.get('version')
            data.generator = elem.get('generator')
        elif elem.tag == 'changeset':
            last_elem = data
        elif elem.tag == 'note':
            data.note = elem.text
        elif elem.tag == 'meta':
            data.meta = dict(elem.attrib)
        elif elem.tag == 'node':
            n = data.Node(float(elem.get('lon')), float(elem.get('lat')), 
                attrs=dict(elem.attrib))
            last_elem = n
        elif elem.tag == 'way':
            w = data.Way(attrs=dict(elem.attrib))
            last_elem = w
        elif elem.tag == 'nd':
            last_elem.nodes.append(elem.get('ref'))
        elif elem.tag == 'relation':
            r = data.Relation(attrs=dict(elem.attrib))
            last_elem = r
        elif elem.tag == 'member':
            last_elem.members.append({
                'ref': elem.get('ref'),
                'type': elem.get('type'),
                'role': elem.get('role')
            })
        elif elem.tag == 'tag':
            last_elem.tags[elem.get('k')] = elem.get('v')
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    for way in data.ways:
        for i, ref in enumerate(way.nodes):
            if 'n{}'.format(ref) in data.index:
                way.nodes[i] = data.get(ref)
    for rel in data.relations:
        for i, m in enumerate(rel.members):
            if isinstance(m, dict):
                if m['type'][0].lower() + str(m['ref']) in data.index:
                    el = data.get(m['ref'], m['type'])
                    rel.members[i] = osm.Relation.Member(el, m['role'])
    return data

