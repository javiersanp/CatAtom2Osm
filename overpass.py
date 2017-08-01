"""Minimum Overpass API interface"""

import re

API_URL = "http://overpass-api.de/api/interpreter?"
#API_URL = "http://overpass.osm.rambler.ru/cgi/interpreter?"


class Query(object):
    """Class for a query to Overpass"""

    def __init__(self, search_area, output='xml', down=True, meta=True):
        """
        Args:
            search_area (str): See set_search_area
            output (str): xml (default) / json
            down (bool): True (default) to include recurse down elements
            meta (bool): True (default) to include metadata
        """
        self.output = 'xml'
        self.down = '(._;>;);' if down else ''
        self.meta = 'out meta;' if meta else 'out;'
        self.area_id = ''
        self.bbox = ''
        self.set_search_area(search_area)
        self.statements = []
        self.url = ''

    def set_search_area(self, search_area):
        """Set the area to search in. It could either the osm id of a named area
           or a bounding box (bottom, left, top, right) clause."""
        if re.match('^\d{1,8}$', search_area):
            self.area_id = search_area
        elif re.match('^(-?\d{1,3}(\.\d+)?,\s*){3}-?\d{1,3}(\.\d+)?$', search_area):
            self.bbox = search_area
        else:
            raise TypeError("Argument expected to be an area id or a bbox "
                            "clause: %s" % search_area)

    def add(self, statement):
        """Adds a statement to the query. Use QL query statements without bbox
           or area clauses. Example: node["name"="Berlin"]"""
        if statement[-1] == ';':
            statement = statement[:-1]
        self.statements.append(statement)
    
    def get_url(self):
        """Returns url for the query"""
        if len(self.statements) > 0:
            ql = '({s});'.join(self.statements) + '({s});'
            if self.area_id:
                query = 'area(36{id:>08})->.searchArea;' + ql
                self.url = query.format(id=self.area_id, s='area.searchArea')
            else:
                self.url = ql.format(s=self.bbox)
        return self.url

