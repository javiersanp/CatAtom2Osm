import unittest
import random

import osm
import osmxml


class OsmxmlTest(unittest.TestCase):

    def test_serialize(self):
        data = osm.Osm()
        data.tags['foo'] = 'bar'
        data.tags['type'] = 'import'
        n = data.Node(4,0)
        n.tags['entrance'] = 'yes'
        n.tags['addr:street'] = 'Calle la X'# pragma: no cover
        n.tags['addr:housenumber'] = '7'
        w = data.Way([(12,0), (14,0), (14,2), (12,2), (12,0)])
        w.tags['leisure'] = 'swiming_pool'
        r = data.MultiPolygon([[
            [(0,0), (10,0), (10,6), (0,6), (0,0)], 
            [(8,1), (9,1), (9,2), (8,2), (8,1)]
        ]])
        r.tags['building'] = 'residential'
        data.new_indexes()
        result = osmxml.serialize(data)
        root = osmxml.etree.fromstring(result)
        self.assertEquals(root.xpath('count(//way)'), 3)
        self.assertEquals(root.xpath('count(//relation)'), 1)
        for (xmltag, osmtag) in zip(root.findall('changeset/tag'), data.tags.items()):
            self.assertEquals(xmltag.attrib['k'], osmtag[0])
            self.assertEquals(xmltag.attrib['v'], osmtag[1])
        for (xmlnode, osmnode) in zip(root.findall('node'), data.nodes):
            self.assertEquals(float(xmlnode.attrib['lon']), osmnode.x) 
            self.assertEquals(float(xmlnode.attrib['lat']), osmnode.y)
        for (xmltag, osmtag) in zip(root.findall('node/tag'), n.tags.items()):
            self.assertEquals(xmltag.attrib['k'], osmtag[0])
            self.assertEquals(xmltag.attrib['v'], osmtag[1])
        for (xmlway, osmway) in zip(root.findall('way'), data.ways):
            for (xmlnd, osmnd) in zip(xmlway.findall('nd'), osmway.nodes):
                self.assertEquals(int(xmlnd.attrib['ref']), osmnd.id)
        for (xmltag, osmtag) in zip(root.findall('way/tag'), w.tags.items()):
            self.assertEquals(xmltag.attrib['k'], osmtag[0])
            self.assertEquals(xmltag.attrib['v'], osmtag[1])
        for (i, (xmlm, osmm)) in enumerate(zip(root.findall('relation/member'), r.members)):
            self.assertEquals(int(xmlm.attrib['ref']), osmm.ref)
            self.assertEquals(xmlm.attrib['role'], 'outer' if i == 0 else 'inner')
        for (xmltag, osmtag) in zip(root.findall('relation/tag'), r.tags.items()):
            self.assertEquals(xmltag.attrib['k'], osmtag[0])
            self.assertEquals(xmltag.attrib['v'], osmtag[1])
