# -*- coding: utf-8 -*-
"""OpenStreetMap data model"""
from collections import defaultdict

# Number of significant decimal digits. 0 to cancel rounding. With a value 
# greater than 7, JOSM give duplicated points errors
COOR_DIGITS = 0


class Osm(object):
    """Class to implement a OSM data set."""

    def __init__(self, upload='never'):
        self.upload = upload
        self.version = '0.6'
        self.generator = None
        self.counter = 0
        self.elements = set()
        self.index = {} # elements by id
        self.tags = {}
        self.note = None
        self.meta = None
        self.attr_list = ('upload', 'version', 'generator')

    @property
    def nodes(self):
        """Returns list of nodes in elements"""
        return [e for e in self.elements if isinstance(e, Node)]

    @property
    def ways(self):
        """Returns list of ways in elements"""
        return [e for e in self.elements if isinstance(e, Way)]

    @property
    def relations(self):
        """Returns list of relations in elements"""
        return [e for e in self.elements if isinstance(e, Relation)]

    @property
    def attrs(self):
        """Returns dictionary of properties in self.attr_list"""
        attrs = {k: getattr(self, k, None) for k in self.attr_list \
            if getattr(self, k, None) is not None}
        return attrs

    def get(self, eid, etype='n'):
        """Returns element by its id"""
        eid = str(eid)
        if eid[0] not in 'nwr': eid = etype[0].lower() + eid
        return self.index[eid]

    def remove(self, el):
        """Remove el from element, from its parents and its orphand childs"""
        self.elements.discard(el)
        del self.index[el.fid]
        parents = self.get_parents()
        for parent in parents[el]:
            parent.remove(el)
        for child in el.childs:
            if not parents[child]:
                self.elements.discard(child)
                del self.index[child.fid]

    def replace(self, n1, n2):
        """Replaces n1 witn n2 in elements."""
        n1.container = None
        self.elements.discard(n1)
        del self.index[n1.fid]
        n2.container = self
        self.elements.add(n2)
        self.index[n2.fid] = n2

    def get_parents(self):
        """Returns a dict of parents for each element"""
        parents = defaultdict(list)
        for el in self.elements:
            if isinstance(el, Way):
                for node in el.nodes:
                    parents[node].append(el)
            elif isinstance(el, Relation):
                for m in el.members:
                    parents[m.element].append(el)
        return parents

    def merge_duplicated(self):
        """Merge elements with the same geometry."""
        parents = self.get_parents()
        geomdupes = defaultdict(list)
        for el in self.elements:
            geomdupes[el.geometry()].append(el)
        for geom, dupes in geomdupes.items():
            if len(dupes) > 1:
                i = 0   # first element in dupes with different tags or id
                while i < len(dupes) -  1 and dupes[i] == geom:
                    i += 1  # see __eq__ method of Element
                for el in dupes:
                    if el is not dupes[i] and el == dupes[i]: 
                        #for parent in el.parents:
                        for parent in parents[el]:
                            parent.replace(el, dupes[i])
                        self.replace(el, dupes[i])
        for way in self.ways:
            way.clean_duplicated_nodes()

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

    def __init__(self, container, tags={}, attrs = None):
        """Each element must belong to a container OSM dataset"""
        self.container = container
        self.action = 'modify'
        self.visible = 'true'
        self.tags = dict((k,v) for (k,v) in tags.items())
        self.version = None
        self.timestamp = None
        self.changeset = None
        self.uid = None
        self.user = None
        self.attr_list = (
            'id', 'action', 'visible', 'version', 
            'timestamp', 'changeset', 'uid', 'user'
        )
        if attrs is not None: self.attrs = attrs
        if not hasattr(self, 'id'):
            container.counter -= 1
            self.id = container.counter
        container.elements.add(self)
        container.index[self.fid] = self

    def __eq__(self, other):
        """Used to determine if two elements could be merged."""
        if isinstance(other, self.__class__):
            a = dict(self.__dict__)
            b = dict(other.__dict__)
            if other.is_new() or self.is_new(): a['id'] = 0
            if other.is_new() or self.is_new(): b['id'] = 0
            if b['tags'] == {}: a['tags'] = {}
            if a['tags'] == {}: b['tags'] = {}
            return a == b
        elif self.is_new() and self.tags == {}:
            return self.geometry() == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_new(self):
        """Returns true if this element is new to OSM"""
        return self.id <= 0

    @property
    def type(self):
        """Returns class name as string"""
        return self.__class__.__name__.lower()

    @property
    def fid(self):
        """Returns id as unique string"""
        return self.type[0] + str(self.id)

    @property
    def attrs(self):
        """Returns the element attributes as a dictionary"""
        attrs = {k: getattr(self, k, None) for k in self.attr_list \
            if getattr(self, k, None) is not None}
        if 'id' in attrs: attrs['id'] = str(attrs['id'])
        return attrs

    @attrs.setter
    def attrs(self, attrs):
        """Sets the element attributes from a dictionary"""
        for (k, v) in attrs.items():
            if k == 'id': v = int(v)
            if k in self.attr_list:
                setattr(self, k, v)


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
        if COOR_DIGITS:
            self.x = round(self.x, COOR_DIGITS)
            self.y = round(self.y, COOR_DIGITS)
        self.attr_list = self.attr_list + ('lon', 'lat')

    def __getitem__(self, key):
        """n[0], n[1] is equivalent to n.x, n.y"""
        if key not in (0,1):
            raise IndexError
        return self.x if key == 0 else self.y

    def geometry(self):
        """Returns pair of coordinates"""
        return (self.x, self.y)

    @property
    def childs(self):
        """Only for simetry with ways and relations"""
        return set()

    @property
    def lon(self):
        """Returns longitude as string"""
        return str(self.x)
    
    @lon.setter
    def lon(self, value):
        """Sets longitude from string"""
        self.x = float(value)

    @property
    def lat(self):
        """Returns latitude as string"""
        return str(self.y)
    
    @lat.setter
    def lat(self, value):
        """Sets latitude from string"""
        self.y = float(value)
    
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

    @property
    def childs(self):
        """Returns set of unique nodes"""
        return set(self.nodes)

    def is_closed(self):
        """Returns true if the way is closed"""
        return len(self.nodes > 2) and self.nodes[0] == self.nodes[-1]

    def is_open(self):
        """Returns true if the way is closed"""
        return not self.is_closed()

    def remove(self, n):
        """Remove n from nodes"""
        self.nodes = [o for o in self.nodes if o is not n]

    def replace(self, n1, n2):
        """Replaces first occurence of node n1 with n2"""
        self.nodes = [n2 if n is n1 else n for n in self.nodes]

    def geometry(self):
        """Returns tuple of coordinates"""
        return tuple(n.geometry() for n in self.nodes)
    
    def clean_duplicated_nodes(self):
        """Removes consecutive duplicate nodes"""
        if self.nodes:
            merged = [self.nodes[0]]
            for i, n in enumerate(self.nodes[1:]):
                if n != self.nodes[i]:
                    merged.append(n)
            self.nodes = merged
    
    def search_node(self, x, y):
        """Returns osm node of way in the given position or None"""
        result = None
        for n in self.nodes:
            if n.x == x and n.y == y:
                result = n
                break
        return result
        

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

    @property
    def childs(self):
        """Returns set of unique members elements"""
        return set([m.element for m in self.members])

    def append(self, element, role=None):
        """Adds a member"""
        self.members.append(Relation.Member(element, role))

    def remove(self, e):
        """Remove e from members"""
        self.members = [m for m in self.members if m.element is not e]

    def replace(self, e1, e2):
        """Replaces first occurence of element e1 with e2"""
        self.members = [Relation.Member(e2, m.role) 
            if m.element == e1 else m for m in self.members]

    def geometry(self):
        """Returns tuple of coordinates"""
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
            if isinstance(self.element, Node):
                return 'node'
            elif isinstance(self.element, Way):
                return 'way'
            return 'relation'
        
        @property
        def ref(self):
            return self.element.id if hasattr(self.element, 'id') else None

        @property
        def attrs(self):
            attrs = dict(type=self.type, ref=str(self.ref))
            if self.role is not None:
                attrs['role'] = self.role
            return attrs


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
