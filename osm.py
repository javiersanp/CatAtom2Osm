# -*- coding: utf-8 -*-
"""OpenStreetMap data model"""
from collections import defaultdict

COOR_DIGITS = 8


class Osm(object):
    """Class to implement a OSM data set."""

    def __init__(self, upload='never'):
        self.upload = upload
        self.version = '0.6'
        self.counter = 0
        self.elements = set()

    @property
    def nodes(self):
        return [e for e in self.elements if isinstance(e, Node)]

    @property
    def ways(self):
        return [e for e in self.elements if isinstance(e, Way)]

    @property
    def relations(self):
        return [e for e in self.elements if isinstance(e, Relation)]

    def merge_duplicated(self):
        """Merge elements with the same geometry."""
        parents = defaultdict(list)  # a dict of parents for each node
        for el in self.elements:
            parents[el].append(self)
            if isinstance(el, Way):
                for node in el.nodes:
                    parents[node].append(el)
            elif isinstance(el, Relation):
                for m in el.members:
                    parents[m.element].append(el)
        geomdupes = defaultdict(list)
        for el in self.elements:
            geomdupes[el.geometry()].append(el)
        for geom, dupes in geomdupes.items():
            if len(dupes) > 1:
                i = 0   # first element in dupes with different tags or id
                while i < len(dupes)-1 and dupes[i] == geom:
                    i += 1  # see __eq__ method of Element
                for el in dupes:
                    if el is not dupes[i] and el == dupes[i]: 
                        for parent in parents[el]:
                            parent.replace(el, dupes[i])

    def new_indexes(self, merge=True):
        """Assign new unique index to each element in the dataset"""
        if merge:   # pragma: no cover
            self.merge_duplicated()
            for way in self.ways:
                way.clean_duplicated_nodes()
        for el in self.elements:
            el.new_index()

    def replace(self, n1, n2):
        """Replaces n1 witn n2 in elements."""
        n1.container = None
        self.elements.discard(n1)
        n2.container = self
        self.elements.add(n2)

    def __getattr__(self, name):
        """
        Helper to create elements.
        Example:
        >>> d = osm.Osm()
        >>> n = d.Node(1,1) # instead of
        >>> n = osm.Node(d, 1, 1)
        """
        if name in ['Node', 'Way', 'Relation', 'Polygon', 'MultiPolygon']:
            cls = globals()[name]
            return lambda *args, **kwargs: cls(self, *args, **kwargs)
        raise AttributeError


class Element(object):
    """Base class for Osm elements"""

    def __init__(self, container, tags={}, action='modify', visible='true'):
        """Each element must belong to a container OSM dataset"""
        self.container = container
        self.action = action
        self.visible = visible
        self.tags = dict((k,v) for (k,v) in tags.items())
        container.elements.add(self)

    def __eq__(self, other):
        """Used to determine if two elements could be merged."""
        if isinstance(other, self.__class__):
            a = dict(self.__dict__)
            b = dict(other.__dict__)
            a['id'] = 0 if 'id' not in b or b['id'] <= 0 else a['id'] if 'id' in a else 0
            b['id'] = 0 if 'id' not in a or a['id'] <= 0 else b['id'] if 'id' in b else 0
            a['tags'] = {} if b['tags'] == {} else a['tags']
            b['tags'] = {} if a['tags'] == {} else b['tags']
            return a == b
        elif not self.is_uploaded() and self.tags == {}:
            return self.geometry() == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def new_index(self):
        """Assign a new unique index if the element is not uploaded (id < 0)"""
        if not hasattr(self, 'id') or self.id <= 0:
            self.container.counter -= 1
            self.id = self.container.counter
    
    def is_uploaded(self):
        return hasattr(self, 'id') and self.id > 0


class Node(Element):
    """A node is a pair of coordinates"""

    def __init__(self, container, x, y=0, *args, **kwargs):
        """Use any of this:
        >>> d = osm.Osm()
        >>> n1 = d.Osm(1,1)
        >>> p = (1,1)
        >>> n2 = d.Osm(p)
        """
        super(Node, self).__init__(container, *args, **kwargs)
        (self.x, self.y) = (x[0], x[1]) \
            if hasattr(x, '__getitem__') else (x, y)
        self.x = round(self.x, COOR_DIGITS)
        self.y = round(self.y, COOR_DIGITS)
            

    def __getitem__(self, key):
        """n[0], n[1] is equivalent to n.x, n.y"""
        if key not in (0,1):
            raise IndexError
        return self.x if key == 0 else self.y

    def geometry(self):
        return (self.x, self.y)

    def __str__(self):
        return str((self.x, self.y))


class Way(Element):
    """A way is a list of nodes"""

    def __init__(self, container, nodes=[], *args, **kwargs):
        """Use any of this:
        >>> d = osm.Osm()
        >>> n1 = d.Node(1,1)
        >>> n2 = d.Node(2,2)
        >>> w = d.Way([n1, n2])
        >>> w = d.Way([(1,1), (2,2)])
        """
        super(Way, self).__init__(container, *args, **kwargs)
        self.nodes = [n if isinstance(n, Node) else Node(container, n) 
            for n in nodes]

    def replace(self, n1, n2):
        """Replaces first occurence of node n1 with n2"""
        self.nodes = [n2 if n == n1 else n for n in self.nodes]

    def geometry(self):
        return tuple(n.geometry() for n in self.nodes)
    
    def clean_duplicated_nodes(self):
        if self.nodes:
            merged = [self.nodes[0]]
            for i, n in enumerate(self.nodes[1:]):
                if n != self.nodes[i]:
                    merged.append(n)
            self.nodes = merged

class Relation(Element):
    """A relation is a collection of nodes, ways or relations"""

    def __init__(self, container, members=[], *args, **kwargs):
        super(Relation, self).__init__(container, *args, **kwargs)
        self.members = []
        for m in members:
            if isinstance(m, Relation.Member):
                self.members.append(m) 
            else:
                self.append(m)

    def append(self, element, role=None):
        self.members.append(Relation.Member(element, role))

    def replace(self, e1, e2):
        """Replaces first occurence of node n1 with n2"""
        self.members = [Relation.Member(e2, m.role) 
            if m.element == e1 else m for m in self.members]

    def geometry(self):
        return tuple(m.element.geometry() for m in self.members)

    class Member(object):
        """A element is member of a relation with a role."""
    
        def __init__(self, element, role=None):
            self.element = element
            self.role = role
        
        def __eq__(self, other):
            """Used to determine if two elements could be merged."""
            if isinstance(other, self.__class__):
                return self.__dict__ == other.__dict__
            else:
                return False

        def __ne__(self, other):
            return not self.__eq__(other)

        @property
        def type(self):
            return self.element.__class__.__name__.lower()
        
        @property
        def ref(self):
            return self.element.id if hasattr(self.element, 'id') else None


class Polygon(Relation):
    """Helper to create a multipolygon type relation with one outer ring and
       many inner rings."""
    
    def __init__(self, container, rings=[], *args, **kwargs):
        super(Polygon, self).__init__(container, *args, **kwargs)
        self.tags['type'] = 'multipolygon'
        role = 'outer'
        for ring in rings:
            if isinstance(ring, Way):
                self.append(ring, role)
            else:
                self.append(Way(container, ring), role)
            role = 'inner'


class MultiPolygon(Polygon):
    """Helper to create a multipolygon type relation with many outer ring and
       many inner rings."""

    def __init__(self, container, parts=[], *args, **kwargs):
        super(MultiPolygon, self).__init__(container, *args, **kwargs)
        for part in parts:
            role = 'outer'
            for ring in part:
                if isinstance(ring, Way):
                    self.append(ring, role)
                else:
                    self.append(Way(container, ring), role)
                role = 'inner'
