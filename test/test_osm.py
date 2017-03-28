import unittest
import random
from collections import Counter

import osm

class OsmTestCase(unittest.TestCase):

    def setUp(self):
        self.d = osm.Osm()


class TestOsm(OsmTestCase):

    def test_init(self):
        self.assertEquals(self.d.counter, 0)
        self.assertEquals(self.d.elements, set())

    def test_getattr(self):
        n = self.d.Node(1,1)
        self.assertEquals((n.x, n.y), (1,1))
        with self.assertRaises(AttributeError):
            self.d.node
        

    def test_properties(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(0,0)
        w = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        r = self.d.Relation([n1, w])
        self.assertEquals(len(self.d.nodes), 6)
        self.assertEquals(self.d.ways, [w])
        self.assertEquals(self.d.relations, [r])

    def test_replace(self):
        n1 = self.d.Node(1,1)
        d2 = osm.Osm()
        n2 = d2.Node(2,2)
        self.d.replace(n1, n2)
        self.assertNotIn(n1, self.d.elements)
        self.assertIn(n2, self.d.elements)
        self.assertEquals(n2.container, self.d)

    def test_merge_duplicated(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(2,2)
        n3 = self.d.Node(3,3, {'a': 'b'})
        n4 = self.d.Node(4,4)
        n4.id = 1
        n5 = self.d.Node(4,4)
        n6 = self.d.Node(4,4)
        n6.id = 2
        n7 = self.d.Node(3,3)
        n8 = self.d.Node(5,5, {'a': '1'})
        n9 = self.d.Node(5,5, {'b': '2'})
        n10 = self.d.Node(5,5)
        w = self.d.Way([(1,1), (1,0), (2,2), (3,2), (3,3)])
        r = self.d.Relation([w, n3])
        self.assertFalse(w.nodes[0] is n1)
        self.assertFalse(w.nodes[2] is n2)
        self.d.merge_duplicated()
        duped = Counter()
        for n in self.d.nodes:
            duped[(n.x, n.y)] += 1
        for position, count in duped.items():
            if position in ((4,4), (5,5)):
                self.assertEquals(count, 2)
            else:
                self.assertEquals(count, 1)
        self.assertIn(w.nodes[0], self.d.elements)
        self.assertIn(w.nodes[2], self.d.elements)
        self.assertEquals(w.nodes[4].tags['a'], 'b')
        self.assertIn(n8, self.d.elements)
        self.assertIn(n9, self.d.elements)

    def test_new_indexes(self):
        w = self.d.Way([(1,1), (1,0), (2,2), (3,2)])
        self.d.new_indexes()
        indexes = []
        for e in self.d.elements:
            self.assertNotIn(e.id, indexes)
            self.assertLess(e.id, 0)
            indexes.append(e.id)


class TestOsmElement(OsmTestCase):

    def test_init(self):
        e1 = osm.Element(self.d, {'foo': 'bar'})
        e2 = osm.Element(self.d)
        self.assertEquals(e1.container, self.d)
        self.assertEquals(e1.tags['foo'], 'bar')

    def test_new_index(self):
        e1 = osm.Element(self.d)
        e2 = osm.Element(self.d)
        e1.new_index()
        e2.new_index()
        self.assertEquals(e1.id, -1)
        self.assertEquals(e2.id, -2)
        e1.id = 1
        e1.new_index()
        self.assertEquals(e1.id, 1)

    def test_is_uploaded(self):
        e = osm.Element(self.d)
        self.assertFalse(e.is_uploaded())
        e.id = -random.randint(0,1000)
        self.assertFalse(e.is_uploaded())
        e.id = random.randint(0,1000)
        self.assertTrue(e.is_uploaded())

class TestOsmNode(OsmTestCase):
    def test_init(self):
        n1 = self.d.Node(1, 2, {'foo': 'bar'})
        self.assertEquals(n1.tags['foo'], 'bar')
        self.assertEquals((n1.x, n1.y), (1, 2))
        n2 = self.d.Node((2,3), tags={'a': 'b'})
        self.assertEquals(n2.tags['a'], 'b')
        self.assertEquals((n2.x, n2.y), (2, 3))

    def test_eq(self):
        n1 = self.d.Node(1, 2)
        self.assertEquals(n1, (1, 2))
        n2 = self.d.Node(1, 2)
        self.assertEquals(n1, n2)
        self.assertEquals(n2, n1)
        n1.tags['a'] = '1'
        n2.tags['a'] = '1'
        self.assertEquals(n1, n2)
        n1.tags = {}
        n2.id = 2
        self.assertEquals(n1, n2)
        
    def test_ne(self):
        n1 = self.d.Node(1, 2, {'c': 'd'})
        n2 = self.d.Node(1, 2, {'a': 'b'})
        self.assertNotEquals(n1, n2)
        self.assertNotEquals(n2, n1)
        n1.tags['a'] = 'b'
        n1.id = 1
        self.assertNotEquals(n1, n2)
        n1.tags = {}
        self.assertNotEquals(n1, (1, 2))
        
    def test_getitem(self):
        n = self.d.Node(1, 2)
        self.assertEquals(n[0], 1)
        self.assertEquals(n[1], 2)
        with self.assertRaises(IndexError):
            n[2]

    def test_geometry(self):
        n = self.d.Node(1,2)
        self.assertEquals(n.geometry(), (1,2))
        
    def test_str(self):
        n = self.d.Node(1, 2)
        self.assertEquals(str(n), str((n.x, n.y)))


class TestOsmWay(OsmTestCase):

    def test_init(self):
        n1 = self.d.Node(1,2)
        n2 = self.d.Node(2,3)
        n3 = self.d.Node(3,4)
        w = self.d.Way([(1,2), n2, (3,4)])
        self.assertEquals(w.nodes, [n1, n2, n3])

    def test_replace(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,2)
        n3 = self.d.Node(2,3)
        n4 = self.d.Node(3,4)
        w = self.d.Way([n1, n2, n4])
        w.replace(n2, n3)
        self.assertEquals(w.nodes, [n1, n3, n4])
        
    def test_eq(self):
        n = self.d.Node(1,1)
        w1 = self.d.Way([n, (2,2), (3,3)])
        w2 = self.d.Way([(1,1), (2,2), (3,3)])
        self.assertEquals(w1, w2)
        n.tags['foo'] = 'bar'
        self.assertEquals(w1, w2)
        
    def test_geometry(self):
        g = ((1,1), (2,2), (3,3))
        w = self.d.Way(g)
        self.assertEquals(w.geometry(), g)
        
    def test_clean_duplicated_nodes(self):
        w = self.d.Way([(0,0), (1,1), (1,1), (2,2)])
        w.clean_duplicated_nodes()
        self.assertEquals(len(w.nodes), 3)
        w = self.d.Way()
        w.clean_duplicated_nodes()
        self.assertEquals(len(w.nodes), 0)
        

class TestOsmRelation(OsmTestCase):

    def test_init(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(0,0)
        w = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        r = self.d.Relation([n1, w, osm.Relation.Member(n2)])
        self.assertEquals(r.members[0].element, n1)
        self.assertEquals(r.members[1].element, w)
        self.assertEquals(r.members[2].element, n2)
        self.assertEquals(r.container, self.d)
        
    def test_append(self):
        n1 = self.d.Node(1,1)
        r = self.d.Relation()
        r.append(n1, 'foobar')
        self.assertEquals(r.members[0].element, n1)
        self.assertEquals(r.members[0].role, 'foobar')
    
    def test_member_eq(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,1)
        m1 = osm.Relation.Member(n1, 'foo')
        m2 = osm.Relation.Member(n1, 'foo')
        self.assertEquals(m1, m2)

    def test_member_ne(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,1)
        m1 = osm.Relation.Member(n1, 'foo')
        m2 = osm.Relation.Member(n1, 'bar')
        m3 = osm.Relation.Member((1,1), 'foo')
        self.assertNotEquals(m1, m2)
        n1.id = 1
        self.assertNotEquals(m1, m3)
        self.assertNotEquals(m1, 'foobar')

    def test_eq(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n, (2,2), (3,3)])
        r1 = self.d.Relation([n, w])
        r2 = self.d.Relation([n, w])
        self.assertEquals(r1, r2)
        
    def test_ne(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n, (2,2), (3,3)])
        r1 = self.d.Relation([n, w])
        r2 = self.d.Relation([n, w])
        r2.append(n, 'foo')
        r2.append(w, 'bar')
        r3 = self.d.Relation([(1,1), w])
        self.assertNotEquals(r1, r2)
        n.id = 1
        self.assertNotEquals(r1, r3)

    def test_geometry(self):
        g1 = ((1,1), (2,2), (3,3))
        w1 = self.d.Way(g1)
        g2 = ((0,0), (1,2), (2,3))
        w2 = self.d.Way(g2)
        n = self.d.Node(4,4)
        r = self.d.Relation([w1, w2, n])
        self.assertEquals(r.geometry(), (g1, g2, (4,4)))

    def test_replace(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,2)
        n3 = self.d.Node(2,3)
        n4 = self.d.Node(3,4)
        r = self.d.Relation([n1, n2, n4])
        r.replace(n2, n3)
        self.assertEquals([m.element for m in r.members], [n1, n3, n4])

    def test_type(self):
        n1 = self.d.Node(1,1)
        m = osm.Relation.Member(n1)
        self.assertEquals(m.type, 'node')
    
    def test_ref(self):
        n1 = self.d.Node(1,1)
        m = osm.Relation.Member(n1)
        self.assertEquals(m.ref, None)
        n1.id = 100
        self.assertEquals(m.ref, 100)


class TestOsmPolygon(OsmTestCase):

    def test_init(self):
        w1 = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        w2 = self.d.Way([(0,0), (1,1), (2,2)])
        p = self.d.Polygon([w1.nodes, w2])
        self.assertEquals(p.members[0].element.nodes, w1.nodes)
        self.assertEquals(p.members[0].role, 'outer')
        self.assertEquals(p.members[1].element, w2)
        self.assertEquals(p.members[1].role, 'inner')


class TestOsmMultiPolygon(OsmTestCase):

    def test_init(self):
        w1 = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        w2 = self.d.Way([(0,0), (1,1), (2,2)])
        w3 = self.d.Way([(11,12), (12,13), (13,12), (11,12)])
        w4 = self.d.Way([(10,10), (11,11), (12,12)])
        p = self.d.MultiPolygon([[w1.nodes, w2], [w3, w4]])
        self.assertEquals(p.members[0].element.nodes, w1.nodes)
        self.assertEquals(p.members[0].role, 'outer')
        self.assertEquals(p.members[1].element, w2)
        self.assertEquals(p.members[1].role, 'inner')
        self.assertEquals(p.members[2].element, w3)
        self.assertEquals(p.members[2].role, 'outer')
        self.assertEquals(p.members[3].element, w4)
        self.assertEquals(p.members[3].role, 'inner')
