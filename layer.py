"""Application layers"""

import os
import math
import re
from collections import defaultdict

from qgis.core import *
from PyQt4.QtCore import QVariant

import setup
import logging
log = logging.getLogger(setup.app_name + ".layer")


class Point(QgsPoint):
    """Extends QgsPoint with some utility methods"""

    def boundingBox(self, radius):
        """Returns a bounding box of 2*radius centered in point."""
        return QgsRectangle(self.x() - radius, self.y() - radius,
                        self.x() + radius, self.y() + radius)

    def is_corner_with_context(self, geom, angle_thr=setup.angle_thr, cath_thr=setup.dist_thr): 
        """
        Test if the nearest vertex in a geometry is a 'corner': if the angle between
        the vertex and their adjacents difers by more than angle_thr of 180 and if 
        the distance from the vertex to the segment formed by their adjacents is 
        greater than cath_thr.
        
        Args:
            geom (QgsGeometry): Geometry to test.
            point (QgsPoint): A point near the vertex we want to test.
            angle_thr (float): Angle threshold.
            cath_thr (float): Cathetus threshold.
        
        Returns:
            (bool) True for a corner, 
            (float) Angle between the vertex and their adjacents,
            (float) Distance from the vertex to the segment formed by their adjacents
        """
        (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(self)
        va = geom.vertexAt(ndxa) # previous vertex
        vb = geom.vertexAt(ndxb) # next vertex
        angle = abs(point.azimuth(va) - point.azimuth(vb))
        a = abs(va.azimuth(point) - va.azimuth(vb))
        h = math.sqrt(va.sqrDist(point))
        c = abs(h * math.sin(math.radians(a)))
        return (abs(180 - angle) > angle_thr or c > cath_thr, angle, c)


class BaseLayer(QgsVectorLayer):
    """Base class for application layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(BaseLayer, self).__init__(path, baseName, providerLib)
        self.writer = self.dataProvider()
        self.rename={}
        self.resolve={}
        self.reference_matchs={}
	
    def copy_feature(self, feature, rename=None, resolve=None):
        """
        Return a copy of feature renaming attributes or resolving xlink references.

        Args:
            feature (QgsFeature): Source feature
            rename (dict): Translation of attributes names
            resolve (dict): xlink reference fields

        Examples:
            With this:
            
            >>> rename = {'spec': 'specification'}
            >>> resolve = {
            ...     'PD_id': ('component_href', '[\w\.]+PD[\.0-9]+'), 
            ...     'TN_id': ('component_href', '[\w\.]+TN[\.0-9]+'), 
            ...     'AU_id': ('component_href', '[\w\.]+AU[\.0-9]+')
            ... }
                
            You get:
            
            >>> original_attributes = ['localId', 'specification', 'component_href']
            >>> original_values = [
            ...     '38.012.1.12.0295603CS6109N', 
            ...     'Parcel', 
            ...     '(3:#ES.SDGC.PD.38.012.38570,#ES.SDGC.TN.38.012.1,#ES.SDGC.AU.38.012)'
            ... ]
            >>> final_attributes = ['localId', 'spec', 'PD_id', 'TN_id', 'AU_id']
            >>> final_values = [
            ...     '38.012.1.12.0295603CS6109N', 
            ...     'Parcel', 
            ...     'ES.SDGC.PD.38.012.38570',
            ...     'ES.SDGC.TN.38.012.1',
            ...     'ES.SDGC.AU.38.012'
            ... ]
        """
        rename = rename if rename is not None else self.rename
        resolve = resolve if resolve is not None else self.resolve
        if self.pendingFields().isEmpty():
            self.dataProvider().addAttributes(feature.fields().toList())
            self.updateFields()
        dst_ft = QgsFeature(self.pendingFields())
        dst_ft.setGeometry(feature.geometry())
        src_attrs = [f.name() for f in feature.fields()]
        for field in self.pendingFields().toList():
            dst_attr = field.name()
            if dst_attr in resolve:
                (src_attr, reference_match) = resolve[dst_attr]
                match = re.search(reference_match, feature[src_attr])
                if match:
                    dst_ft[dst_attr] = match.group(0)
            else:
                src_attr = dst_attr
                if dst_attr in rename:
                    src_attr = rename[dst_attr]
                if src_attr in src_attrs:
                    dst_ft[dst_attr] = feature[src_attr]
        return dst_ft
    
    def append(self, layer, rename=None, resolve=None, query=None):
        """Copy all features from layer.

        Args:
            layer (QgsVectorLayer): Source layer
            rename (dict): Translation of attributes names
            resolve (dict): xlink reference fields
            query (func):

        Examples:

            >>> query = lambda feat: feat['foo']=='bar'
            
            Will copy only features with a value 'bar' in the field 'foo'.
            
            See also copy_feature().
        """
        self.setCrs(layer.crs())
        self.startEditing()
        for feature in layer.getFeatures():
            if not query or query(feature):
                self.addFeature(self.copy_feature(feature, rename, resolve))
        self.commitChanges()

    def reproject(self, target_crs=None):
        """Reproject all features in this layer to a new CRS.

        Args:
            target_crs (QgsCoordinateReferenceSystem): New CRS to apply.
        """
        if target_crs is None:
            target_crs = QgsCoordinateReferenceSystem(4326)
        crs_transform = QgsCoordinateTransform(self.crs(), target_crs)
        out_feat = QgsFeature()
        self.startEditing()
        for feature in self.getFeatures():
            geom = feature.geometry()
            geom.transform(crs_transform)
            out_feat.setGeometry(geom)
            out_feat.setAttributes(feature.attributes())
            self.writer.addFeatures([out_feat])
            self.writer.deleteFeatures([feature.id()])
        self.setCrs(target_crs)
        self.commitChanges()
        self.updateExtents()
    
    def join_field(self, source_layer, target_field_name, join_field_name, 
            field_names_subset, prefix = ""):
        """
        Replaces qgis table join mechanism becouse I'm not able to work with it 
        in standalone script mode (without GUI).
        
        Args:
            source_layer (QgsVectorLayer): Source layer.
            target_field_name (str): Join field in the target layer. 
            join_fieldsName (str): Join field in the source layer.
            field_names_subset (list): List of field name strings for the target layer.
            prefix (str): An optional prefix 
        """
        self.startEditing()
        fields = []
        target_attrs = [f.name() for f in self.pendingFields()]
        for attr in field_names_subset:
            field = source_layer.pendingFields().field(attr)
            if field.length > 254:
                field.setLength(254)
            field.setName(prefix + attr)
            if field.name() not in target_attrs:
                fields.append(field)
        self.writer.addAttributes(fields)
        self.updateFields()
        source_values = {}
        for feature in source_layer.getFeatures():
            source_values[feature[join_field_name]] = \
                    {attr: feature[attr] for attr in field_names_subset}
        for feature in self.getFeatures():
            attrs = {}
            for attr in field_names_subset:
                fieldId = feature.fieldNameIndex(prefix + attr)
                if feature[target_field_name] in source_values:
                    value = source_values[feature[target_field_name]][attr]
                else:
                    value = None
                attrs[fieldId] = value 
            self.writer.changeAttributeValues({feature.id(): attrs})
        self.commitChanges()

    def export(self, path, driver_name="ESRI Shapefile", overwrite=True):
        """Write layer to file

        Args:
            path (str): Path of the output file
            driver_name (str): Defaults to ESRI Shapefile.
            overwrite (bool): Defaults to True
        """
        if os.path.exists(path) and overwrite:
            if driver_name == 'ESRI Shapefile':
                QgsVectorFileWriter.deleteShapeFile(path)
            else:
                os.remove(path)
        return QgsVectorFileWriter.writeAsVectorFormat(self, path, "utf-8", 
                self.crs(), driver_name) == QgsVectorFileWriter.NoError

    def search(self, expression):
        """Returns a features list for this search expression
        """
        exp = QgsExpression(expression)
        request = QgsFeatureRequest(exp)
        return self.getFeatures(request)


class PolygonLayer(BaseLayer):
    """Base class for polygon layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(PolygonLayer, self).__init__(path, baseName, providerLib)
        self.dup_thr = setup.dup_thr # Distance in meters to merge nearest vertex.
        self.cath_thr = setup.dist_thr # Threshold in meters for cathetus reduction
        self.angle_thr = setup.angle_thr # Threshold in degrees from straight angle to delete a vertex
        self.dist_thr = setup.dist_thr # Threshold for topological points.

    def explode_multi_parts(self):
        """
        Creates a new WKBPolygon feature for each part of any WKBMultiPolygon 
        feature in the layer. This avoid relations with may 'outer' members in
        OSM data set. From this moment, localId will not be a unique identifier
        for buildings.

        Returns:
            (int) count of multi-polygons, (int) count of parts
        """
        self.startEditing()
        to_clean = []
        to_add = []
        for feature in self.getFeatures():
            geom = feature.geometry()
            if geom.wkbType() == QGis.WKBMultiPolygon:
                for part in geom.asMultiPolygon():
                    feat = QgsFeature(feature)
                    feat.setGeometry(QgsGeometry.fromPolygon(part))
                    to_add.append(feat)
                to_clean.append(feature.id())
        self.writer.deleteFeatures(to_clean)
        self.writer.addFeatures(to_add)
        self.commitChanges()
        return (len(to_clean), len(to_add))

    def get_parents_per_vertex_and_features(self):
        """
        Returns:
            (dict) parent fids for each vertex, (dict) feature for each fid.
        """
        parents_per_vertex = defaultdict(list)
        features = {}
        for feature in self.getFeatures(): 
            features[feature.id()] = feature
            geom = feature.geometry()
            for ring in geom.asPolygon():
                for point in ring[0:-1]:
                    parents_per_vertex[point].append(feature.id())
        return (parents_per_vertex, features)
    
    def get_adjacents_and_features(self):
        """
        Returns:
            (list) groups of fids of adjacent polygons, (dict) feature for each fid.
        """
        (parents_per_vertex, features) = self.get_parents_per_vertex_and_features()
        adjs = []
        for (point, parents) in parents_per_vertex.items():
            if len(parents) > 1:
                for fid in parents:
                    geom = features[fid].geometry()
                    (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(point)
                    next = geom.vertexAt(ndxb)
                    parents_next = parents_per_vertex[next]
                    common = set(x for x in parents if x in parents_next)
                    if len(common) > 1:
                        adjs.append(common)
        adjs = list(adjs)
        groups = []
        while adjs:
            group = set(adjs.pop())
            lastlen = -1
            while len(group) > lastlen:
                lastlen = len(group)
                for adj in adjs[:]:
                    if len({p for p in adj if p in group}) > 0:
                        group |= adj
                        adjs.remove(adj)
            groups.append(group)
        return (groups, features)
    
    def get_vertices(self):
        """Returns a in memory layer with the coordinates of each vertex"""
        vertices = QgsVectorLayer("Point", "vertices", "memory")
        vertices.startEditing() # layer with the coordinates of each vertex
        for feature in self.getFeatures(): 
            for ring in feature.geometry().asPolygon():
                for point in ring[0:-1]:
                    feat = QgsFeature(QgsFields())
                    geom = QgsGeometry.fromPoint(point)
                    feat.setGeometry(geom)
                    vertices.addFeature(feat)
        vertices.commitChanges()
        return vertices
    
    def get_duplicates(self, dup_thr=None):
        """
        Returns a dict of duplicated vertices for each coordinate.
        Two vertices are duplicated if they are nearest than dup_thr.
        """
        vertices = self.get_vertices()
        vertices_by_fid = {feat.id(): feat for feat in vertices.getFeatures()}
        #index = QgsSpatialIndex()
        index = QgsSpatialIndex(vertices.getFeatures())
        dup_thr = self.dup_thr if dup_thr is None else dup_thr
        duplicates = defaultdict(list)
        for vertex in vertices.getFeatures():
            point = Point(vertex.geometry().asPoint())
            area_of_candidates = point.boundingBox(dup_thr)
            fids = index.intersects(area_of_candidates)
            for fid in fids:
                dup = vertices_by_fid[fid].geometry().asPoint()
                dist = point.sqrDist(dup)
                if dup != point and dist < dup_thr**2:
                    duplicates[point].append(dup)
        return duplicates
        
    def merge_duplicates(self):
        """
        Reduces the number of vertices in a polygon layer merging vertices nearest 
        than 'dup_thr' meters.

        Returns:
            (int) count of duplicated vertices
        """
        dup_thr = self.dup_thr
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_duplicated.shp", self.crs())
        (parents_per_vertex, features) = self.get_parents_per_vertex_and_features()
        dupes = 0
        duplicates = self.get_duplicates()
        self.startEditing()
        duplist = sorted(duplicates.keys(), key=lambda x: -len(duplicates[x]))
        for point in duplist:
            for dup in duplicates[point]:
                for fid in parents_per_vertex[dup]:
                    feat = features[fid]
                    geom = feat.geometry()
                    (p, ndx, ndxa, ndxb, dist) = geom.closestVertex(dup)
                    if geom.moveVertex(point.x(), point.y(), ndx):
                        dupes += 1
                        if log.getEffectiveLevel() <= logging.DEBUG:
                            debshp.add_point(p, "Merge. %s" % feat['localId'])
                        self.writer.changeGeometryValues({fid: geom})
                if dup in duplist:
                    duplist.remove(dup)
        self.commitChanges()
        return dupes

    def clean_duplicated_nodes_in_polygons(self):
        """
        Cleans consecutives nodes with the same coordinates in any ring of a 
        polygon.

        Returns:
            (int) count of duplicated vertices
        """
        dupes = 0
        self.startEditing()
        for feature in self.getFeatures(): 
            geom = feature.geometry()
            replace = False
            new_polygon = []
            for ring in geom.asPolygon():
                if ring:
                    merged = [ring[0]]
                    for i, point in enumerate(ring[1:]):
                        if point == ring[i]:
                            dupes += 1
                            replace=True
                        else:
                            merged.append(point)
                    new_polygon.append(merged)
            if replace:
                new_geom = QgsGeometry().fromPolygon(new_polygon)
                self.writer.changeGeometryValues({feature.id(): new_geom})
        self.commitChanges()
        return dupes

    def add_topological_points(self):
        """
        For each vertex in a polygon layer, adds it to nearest segments.

        Returns:
            (int) count of topological points added
        """
        threshold = self.dist_thr # Distance threshold to create nodes
        angle_thr = self.angle_thr
        tp = 0
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_topology.shp", self.crs())
        #index = QgsSpatialIndex()
        index = QgsSpatialIndex(self.getFeatures())
        features = {feat.id(): feat for feat in self.getFeatures()}

        self.startEditing()
        for feature in features.values():
            geom = feature.geometry()
            for point in geom.asPolygon()[0][0:-1]: # excludes inner rings and last point:
                area_of_candidates = Point(point).boundingBox(threshold)
                for fid in index.intersects(area_of_candidates):
                    candidate = features[fid]
                    if fid != feature.id():
                        distance, closest, vertex = candidate.geometry() \
                                .closestSegmentWithContext(point)
                        g = candidate.geometry()
                        va = g.vertexAt(vertex)
                        vb = g.vertexAt(vertex - 1)
                        if distance < threshold**2 and point <> va and point <> vb:
                            note = "refused by angle"
                            angle = abs(point.azimuth(va) - point.azimuth(vb))
                            if abs(180 - angle) <= angle_thr:
                                note = "refused by insertVertex"
                                if g.insertVertex(point.x(), point.y(), vertex):
                                    note = "refused by isGeosValid"
                                    if g.isGeosValid():
                                        note = "accepted"
                                        tp += 1
                                        self.writer.changeGeometryValues({fid: g})
                            if log.getEffectiveLevel() <= logging.DEBUG:
                                debshp.add_point(point, note)
        self.commitChanges()

        if log.getEffectiveLevel() <= logging.DEBUG:
            del debshp
        return tp


    def simplify(self):
        """
        Reduces the number of vertices in a polygon layer according to:

        * Delete vertex if the distance to the segment formed by its parents is
          less than 'cath_thr' meters.

        * Delete vertex if the angle with its parent is near of the straight 
          angle for less than 'angle_thr' degrees.

        Returns:
            (int) count of simplified vertices
        """
        cath_thr = self.cath_thr
        angle_thr = self.angle_thr
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_simplify.shp", self.crs())
        index = QgsSpatialIndex()
        index = QgsSpatialIndex(self.getFeatures())
        (parents_per_vertex, features) = self.get_parents_per_vertex_and_features()
        killed = 0
        dupes = 0
        self.startEditing()
        for pnt, parents in parents_per_vertex.items():
            # Test if this vertex is a 'corner' in any of its parent polygons
            point = Point(pnt)
            deb_values = []
            corners = 0
            for fid in parents:
                feat = features[fid]
                geom = feat.geometry()
                (is_corner, angle, cath) = point.is_corner_with_context(geom)
                deb_values.append((is_corner, angle, cath))
                if is_corner:
                    corners += 1
                    break
            if corners == 0:     # If not is a corner
                killed += 1      # delete the vertex from all its parents.
                for fid in frozenset(parents):
                    feat = features[fid]
                    geom = feat.geometry()
                    (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(point)
                    if (geom.deleteVertex(ndx)):
                        parents.remove(fid)
                        self.writer.changeGeometryValues({fid: geom})
                if log.getEffectiveLevel() <= logging.DEBUG:
                    msg = str(["%s angle=%.1f, cath=%.4f" % v for v in deb_values])
                    debshp.add_point(point, "Deleted. %s" % msg)
            elif log.getEffectiveLevel() <= logging.DEBUG:
                msg = str(["%s angle=%.1f, cath=%.4f" % v for v in deb_values])
                debshp.add_point(point, "Keep. %s" % msg)
        self.commitChanges()
        return killed

    def merge_adjacents(self):
        """
        Merge polygons with shared vertices

        Returns:
            (int) count of adjacent polygons, (int) count of merged polygons
        """
        (groups, features) = self.get_adjacents_and_features()
        self.startEditing()
        cleaned = added = 0
        for group in groups:
            group = list(group)
            geom = features[group[0]].geometry()
            for fid in group[1:]:
                geom = geom.combine(features[fid].geometry())
            self.writer.deleteFeatures(group[1:])
            self.writer.changeGeometryValues({group[0]: geom})
            added += 1
            cleaned += len(group)
        self.commitChanges()
        return (cleaned, added)


class ParcelLayer(BaseLayer):
    """Class for cadastral parcels"""

    def __init__(self, path="Polygon", baseName="cadastralparcel", providerLib="memory"):
        super(ParcelLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.dataProvider().addAttributes([
                    QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}


class ZoningLayer(PolygonLayer):
    """Class for cadastral zoning"""

    def __init__(self, path="Polygon", baseName="cadastralzoning", providerLib="memory"):
        super(ZoningLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.dataProvider().addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
                QgsField('level', QVariant.String, len=254),
                QgsField('levelName', QVariant.String, len=254),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}

    def set_labels(self, str_format):
        """Asigns a sequence of integers to the label field.

        Args:
            str_format (string): Text format for the label field.
        """
        self.startEditing()
        i = 1
        for feat in self.getFeatures():
            self.changeAttributeValue(feat.id(), self.fieldNameIndex('label'), 
                str_format % i)
            i += 1
        self.commitChanges()

    @staticmethod
    def clasify_zoning(zoning):
        """Splits zones acording to levelName. 'MANZANA' zones corresponds to 
        Urban Cadastre and 'POLIGONO' zones to Rustic Cadastre.

        Args:
            zoning (QgsVectorLayer): CadastralZoning data set
        
        Returns:
            (ZoningLayer) Urban zoning, (ZoningLayer) Rustic zoning
        """
        urban_zoning = ZoningLayer(baseName='urbanzoning')
        rustic_zoning = ZoningLayer(baseName='rusticzoning')
        urban_query = lambda feat: feat['levelName'][3] == 'M' # "(1:MANZANA )"
        rustic_query = lambda feat: feat['levelName'][3] == 'P' # "(1:POLIGONO )"
        urban_zoning.append(zoning, query=urban_query)
        rustic_zoning.append(zoning, query=rustic_query)
        return urban_zoning, rustic_zoning


class AddressLayer(BaseLayer):
    """Class for address"""

    def __init__(self, path="Point", baseName="address", 
            providerLib = "memory"):
        super(AddressLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.dataProvider().addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('spec', QVariant.String, len=254),
                QgsField('designator', QVariant.String, len=254),
                QgsField('PD_id', QVariant.String, len=254),
                QgsField('TN_id', QVariant.String, len=254),
                QgsField('AU_id', QVariant.String, len=254)
            ])
            self.updateFields()
        self.rename = {'spec': 'specification'}
        self.resolve = {
            'PD_id': ('component_href', '[\w\.]+PD[\.0-9]+'), 
            'TN_id': ('component_href', '[\w\.]+TN[\.0-9]+'), 
            'AU_id': ('component_href', '[\w\.]+AU[\.0-9]+')
        }


class ConsLayer(PolygonLayer):
    """Class for constructions"""

    def __init__(self, path="Polygon", baseName="building", 
            providerLib = "memory"):
        super(ConsLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.dataProvider().addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('condition', QVariant.String, len=254),
                QgsField('link', QVariant.String, len=254),
                QgsField('currentUse', QVariant.String, len=254),
                QgsField('bu_units', QVariant.Int),
                QgsField('dwellings', QVariant.Int),
                QgsField('lev_above', QVariant.Int),
                QgsField('lev_below', QVariant.Int),
                QgsField('nature', QVariant.String, len=254),
                QgsField('task', QVariant.String, len=254)
            ])
            self.updateFields()
        self.rename = {
            'condition': 'conditionOfConstruction', 
            'link': 'documentLink' ,
            'bu_units': 'numberOfBuildingUnits', 
            'dwellings': 'numberOfDwellings',
            'lev_above': 'numberOfFloorsAboveGround',
            'lev_below': 'numberOfFloorsBelowGround',
            'nature': 'constructionNature'
        }

    @staticmethod
    def is_building(feature):
        """Building features have not any underscore in its localId field"""
        return '_' not in feature['localId']

    @staticmethod
    def is_part(feature):
        """Part features have '_part' in its localId field"""
        return '_part' in feature['localId']

    def remove_parts_below_ground(self):
        """Remove all parts with 'lev_above' field equal 0."""
        self.startEditing()
        to_clean = [f.id() for f in self.search('lev_above=0')]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
        self.commitChanges()
        return len(to_clean)
        
    def merge_greatest_part(self, footprint, parts):
        """
        Given a building footprint and its parts:
        
        * Exclude parts not inside the footprint.
        
        * If the area of the parts above ground is equal to the area of the 
          footprint.
          
          * Sum the area for all the parts with the same level. Level is the 
            pair of values 'lev_above' and 'lev_below' (number of floors 
            above, and below groud).
            
          * For the level with greatest area, translate the number of floors 
            values to the footprint and deletes all the parts in that level.
        """
        parts_inside_footprint = [part for part in parts 
            if footprint.geometry().contains(part.geometry())
                or footprint.geometry().overlaps(part.geometry())]
        area_for_level = defaultdict(list)
        for part in parts_inside_footprint:
            level = (part['lev_above'], part['lev_below'])
            area = part.geometry().area()
            if level[0] > 0:
                area_for_level[level].append(area)
        parts_merged = 0
        if area_for_level:
            footprint_area = round(footprint.geometry().area()*100)
            parts_area = round(sum(sum(v) for v in area_for_level.values())*100)
            if footprint_area == parts_area:
                level_with_greatest_area = max(area_for_level.iterkeys(), key=(lambda level: sum(area_for_level[level])))
                to_clean = []
                for part in parts_inside_footprint:
                    if (part['lev_above'], part['lev_below']) == level_with_greatest_area:
                        to_clean.append(part.id())
                if to_clean:
                    self.changeAttributeValue(footprint.id(), 
                        self.fieldNameIndex('lev_above'), level_with_greatest_area[0])
                    self.changeAttributeValue(footprint.id(), 
                        self.fieldNameIndex('lev_below'), level_with_greatest_area[1])
                    self.writer.deleteFeatures(to_clean)
                parts_merged = len(to_clean)
        return parts_merged

    def index_of_building_and_parts(self):
        """
        Constructs some utility dicts.
        features index feature by fid.
        buildings index building by localid (many if it was a multipart building).
        parts index parts of building by building localid.
        """
        features = {}
        buildings = defaultdict(list)
        parts = defaultdict(list)
        for feature in self.getFeatures():
            features[feature.id()] = feature
            if self.is_building(feature):
                buildings[feature['localId']].append(feature.id())
            elif self.is_part(feature):
                localId = feature['localId'].split('_')[0]
                parts[localId].append(feature.id())
        return (features, buildings, parts)
    
    def merge_building_parts(self):
        """Apply merge_greatest_part to each set of building and its parts"""
        parts_merged = 0
        (features, buildings, parts) = self.index_of_building_and_parts()
        self.startEditing()
        for (localId, fids) in buildings.items():
            if localId in parts:
                for fid in fids:
                    building = features[fid]
                    parts_for_building = [features[i] for i in parts[localId]]
                    parts_merged += \
                        self.merge_greatest_part(building, parts_for_building)
        self.commitChanges()
        return parts_merged

    def set_tasks(self, urban_zoning, rustic_zoning):
        """Assings to the 'task' field the label of the zone that each feature 
        is contained. Buildings within or adjacent to an urban zone receives an 
        urban zone label, buildings within an rustic zone that have not been
        previously labeled receives a rustic zone label. Building task label
        is propagated to its parts.
        """
        (features, buildings, parts) = self.index_of_building_and_parts()
        index = QgsSpatialIndex(self.getFeatures())
        self.startEditing()
        updated = set()
        prefix = urban_zoning.name()[0].upper()
        tf = self.fieldNameIndex('task')
        for task in urban_zoning.getFeatures():
            zone = task.geometry()
            for fid in index.intersects(zone.boundingBox()):
                candidate = features[fid]
                if not candidate['task'] and (zone.overlaps(candidate.geometry()) 
                        or zone.contains(candidate.geometry())):
                    features[fid]['task'] = prefix + task['label']
                    self.changeAttributeValue(fid, tf, prefix + task['label'])
                    updated.add(fid)
                    if self.is_building(candidate):
                        for i in parts[candidate['localId']]:
                            features[i]['task'] = prefix + task['label']
                            self.changeAttributeValue(i, tf, prefix + task['label'])
                            updated.add(i)
        prefix = rustic_zoning.name()[0].upper()
        for task in rustic_zoning.getFeatures():
            zone = task.geometry()
            for fid in index.intersects(zone.boundingBox()):
                candidate = features[fid]
                if not candidate['task'] and zone.contains(candidate.geometry()):
                    features[fid]['task'] = prefix + task['label']
                    self.changeAttributeValue(fid, tf, prefix + task['label'])
                    updated.add(fid)
        self.commitChanges()
        return len(updated)


class DebugWriter(QgsVectorFileWriter):
    """A QgsVectorFileWriter for debugging purposess."""

    def __init__(self, filename, crs, driver_name="ESRI Shapefile"):
        """
        Args:
            filename (str): File name of the layer
            crs (QgsCoordinateReferenceSystem): Crs of layer.
            driver_name (str): Defaults to ESRI Shapefile.
        """
        self.fields = QgsFields()
        self.fields.append(QgsField("note", QVariant.String, len=100))
        QgsVectorFileWriter.__init__(self, filename, "utf-8", self.fields, 
                QGis.WKBPoint, crs, driver_name)
    
    def add_point(self, point, note=None):
        """Adds a point to the layer with the attribute note."""
        feat = QgsFeature(QgsFields(self.fields))
        geom = QgsGeometry.fromPoint(point)
        feat.setGeometry(geom)
        if note:
            feat.setAttribute("note", note[:254])
        return self.addFeature(feat)

