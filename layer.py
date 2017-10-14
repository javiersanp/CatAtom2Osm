# -*- coding: utf-8 -*-
"""Application layers"""

import os
import math
import re
from collections import defaultdict, Counter
import logging

from qgis.core import *
from PyQt4.QtCore import QVariant

import hgwnames
import osm
import setup
import translate
log = logging.getLogger(setup.app_name + "." + __name__)

BUFFER_SIZE = 512

is_inside = lambda f1, f2: \
    f2.geometry().contains(f1.geometry()) or f2.geometry().overlaps(f1.geometry())

get_attributes = lambda feat: \
    dict([(i, feat[i]) for i in range(len(feat.fields().toList()))])


class Point(QgsPoint):
    """Extends QgsPoint with some utility methods"""

    def __init__(self, arg1, arg2=None):
        if arg2 is None:
            super(Point, self).__init__(arg1[0], arg1[1])
        else:
            super(Point, self).__init__(arg1, arg2)

    def boundingBox(self, radius):
        """Returns a bounding box of 2*radius centered in point."""
        return QgsRectangle(self.x() - radius, self.y() - radius,
                        self.x() + radius, self.y() + radius)

    def get_angle_with_context(self, geom, acute_thr=setup.acute_thr,
            straight_thr=setup.straight_thr, cath_thr=setup.dist_thr):
        """
        For the vertex in a geometry nearest to this point, give the angle
        between its adjacent vertexs.

        Args:
            geom (QgsGeometry): Geometry to test.
            acute_thr (float): Acute angle threshold.
            straight_thr (float): Straight angle threshold.
            cath_thr (float): Cathetus threshold.

        Returns:
            (float) Angle between the vertex and their adjacents,
            (bool)  True for a corner (the angle differs by more than straight_thr
            of 180 and if the distance from the vertex to the segment formed by
            their adjacents is greater than cath_thr.
            (bool)  True if the angle is too low (< acute_thr)
            (float) Distance from the vertex to the segment formed by their adjacents
        """
        (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(self)
        va = geom.vertexAt(ndxa) # previous vertex
        vb = geom.vertexAt(ndxb) # next vertex
        angle = abs(point.azimuth(va) - point.azimuth(vb))
        a = abs(va.azimuth(point) - va.azimuth(vb))
        h = math.sqrt(va.sqrDist(point))
        c = abs(h * math.sin(math.radians(a)))
        is_corner = abs(180 - angle) > straight_thr and c > cath_thr
        is_acute = angle < acute_thr if angle < 180 else 360 - angle < acute_thr
        return (angle, is_acute, is_corner, c)


class BaseLayer(QgsVectorLayer):
    """Base class for application layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(BaseLayer, self).__init__(path, baseName, providerLib)
        self.writer = self.dataProvider()
        self.rename={}
        self.resolve={}
        self.reference_matchs={}

    @staticmethod
    def create_shp(name, crs, fields=QgsFields(), geom_type=QGis.WKBMultiPolygon):
        QgsVectorFileWriter(name, 'UTF-8', fields, geom_type, crs, 'ESRI Shapefile')

    def __del__(self):
        if log.getEffectiveLevel() > logging.DEBUG and \
                self.writer.storageType() == 'ESRI Shapefile':
            path = self.writer.dataSourceUri().split('|')[0]
            QgsVectorFileWriter.deleteShapeFile(path)
            path = os.path.splitext(path)[0] + '.cpg'
            if os.path.exists(path):
                os.remove(path)
            
    def get_feature(self, fid):
        request = QgsFeatureRequest().setFilterFids([fid])
        return self.getFeatures(request).next()

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
            self.writer.addAttributes(feature.fields().toList())
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

    def append(self, layer, rename=None, resolve=None, query=None, **kwargs):
        """Copy all features from layer.

        Args:
            layer (QgsVectorLayer): Source layer
            rename (dict): Translation of attributes names
            resolve (dict): xlink reference fields
            query (func): function with args feature and kwargs that returns
                a boolean deciding if each feature will be included or not
            kwargs: aditional arguments for query function

        Examples:

            >>> query = lambda feat, kwargs: feat['foo']=='bar'
            Will copy only features with a value 'bar' in the field 'foo'.
            >>> query = lambda feat, kwargs: layer.is_inside(feat, kwargs['zone'])
            Will copy only features inside zone.

            See also copy_feature().
        """
        self.setCrs(layer.crs())
        total = 0
        to_add = []
        for feature in layer.getFeatures():
            if not query or query(feature, kwargs):
                to_add.append(self.copy_feature(feature, rename, resolve))
                total += 1
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
        if len(to_add) > 0:
            self.writer.addFeatures(to_add)
        if total:
            log.debug (_("Loaded %d features in '%s' from '%s'"), total,
                self.name().encode('utf-8'), layer.name().encode('utf-8'))

    def reproject(self, target_crs=None):
        """Reproject all features in this layer to a new CRS.

        Args:
            target_crs (QgsCoordinateReferenceSystem): New CRS to apply.
        """
        if target_crs is None:
            target_crs = QgsCoordinateReferenceSystem(4326)
        crs_transform = QgsCoordinateTransform(self.crs(), target_crs)
        to_change = {}
        for feature in self.getFeatures():
            geom = QgsGeometry(feature.geometry())
            geom.transform(crs_transform)
            to_change[feature.id()] = geom
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_change)
                to_change = {}
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)
        self.setCrs(target_crs)
        self.updateExtents()
        if self.writer.storageType() == 'ESRI Shapefile':
            path = self.writer.dataSourceUri().split('|')[0]
            path = os.path.splitext(path)[0]
            if os.path.exists(path + '.prj'):
                os.remove(path + '.prj')
            if os.path.exists(path + '.qpj'):
                os.remove(path + '.qpj')
        log.debug(_("Reprojected the '%s' layer to '%s' CRS"),
            self.name().encode('utf-8'), target_crs.description())

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
            prefix (str): An optional prefix to add to the target fields names
        """
        fields = []
        target_attrs = [f.name() for f in self.pendingFields()]
        for attr in field_names_subset:
            field = source_layer.pendingFields().field(attr)
            field.setName(prefix + attr)
            if field.name() not in target_attrs:
                if field.length() > 254:
                    field.setLength(254)
                fields.append(field)
        self.writer.addAttributes(fields)
        self.updateFields()
        source_values = {}
        for feature in source_layer.getFeatures():
            source_values[feature[join_field_name]] = \
                    {attr: feature[attr] for attr in field_names_subset}
        total = 0
        to_change = {}
        for feature in self.getFeatures():
            attrs = {}
            for attr in field_names_subset:
                fieldId = feature.fieldNameIndex(prefix + attr)
                value = None
                if feature[target_field_name] in source_values:
                    value = source_values[feature[target_field_name]][attr]
                attrs[fieldId] = value
            to_change[feature.id()] = attrs
            total += 1
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeAttributeValues(to_change)
                to_change = {}
        if len(to_change) > 0:
            self.writer.changeAttributeValues(to_change)
        if total:
            log.debug(_("Joined '%s' to '%s'"), source_layer.name().encode('utf-8'),
                self.name().encode('utf-8'))

    def translate_field(self, field_name, translations, clean=True):
        """
        Transform the values of a field

        Args:
            field_name (str): Name of the field to transform
            translations (dict): A dictionary used to transform field values
            clean (bool): If true (default), delete features without translation
        """
        field_ndx = self.pendingFields().fieldNameIndex(field_name)
        if field_ndx >= 0:
            to_clean = []
            to_change = {}
            for feat in self.getFeatures():
                value = feat[field_name]
                if value in translations and translations[value] != '':
                    new_value = translations[value]
                    feat[field_name] = new_value
                    to_change[feat.id()] = get_attributes(feat)
                elif clean:
                    to_clean.append(feat.id())
            self.writer.changeAttributeValues(to_change)
            self.writer.deleteFeatures(to_clean)

    def get_index(self):
        """Returns a QgsSpatialIndex of all features in this layer (overpass 
        QGIS exception for void layers)"""
        if self.featureCount() > 0:
            return QgsSpatialIndex(self.getFeatures())
        else:
            return QgsSpatialIndex()

    def bounding_box(self):
        bbox = None
        for f in self.getFeatures():
            if bbox is None:
                bbox = f.geometry().boundingBox()
            else:
                bbox.combineExtentWith(f.geometry().boundingBox())
        if bbox:
            p1 = QgsGeometry().fromPoint(Point(bbox.xMinimum(), bbox.yMinimum()))
            p2 = QgsGeometry().fromPoint(Point(bbox.xMaximum(), bbox.yMaximum()))
            target_crs = QgsCoordinateReferenceSystem(4326)
            crs_transform = QgsCoordinateTransform(self.crs(), target_crs)
            p1.transform(crs_transform)
            p2.transform(crs_transform)
            bbox = [p1.asPoint().y(), p1.asPoint().x(), p2.asPoint().y(), p2.asPoint().x()]
            bbox = '{:.8f},{:.8f},{:.8f},{:.8f}'.format(*bbox)
        return bbox

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

    def to_osm(self, tags_translation=translate.all_tags, data=None, upload='never'):
        """
        Export this layer to an Osm data set

        Args:
            tags_translation (function): Function to translate fields to tags.
                By defaults convert all fields.
            data (Osm): OSM data set to append. By default creates a new one.
            upload (str): upload attribute of the osm dataset, default 'never'

        Returns:
            Osm: OSM data set
        """
        if data is None:
            data = osm.Osm(upload)
            nodes = ways = relations = 0
        else:
            nodes = len(data.nodes)
            ways = len(data.ways)
            relations = len(data.relations)
        for feature in self.getFeatures():
            geom = feature.geometry()
            e = None
            if geom.wkbType() == QGis.WKBPolygon:
                pol = geom.asPolygon()
                if len(pol) == 1:
                    e = data.Way(pol[0])
                else:
                    e = data.Polygon(pol)
            elif geom.wkbType() == QGis.WKBMultiPolygon:
                e = data.MultiPolygon(geom.asMultiPolygon())
            elif geom.wkbType() == QGis.WKBPoint:
                e = data.Node(geom.asPoint())
            else:
                log.warning(_("Detected a %s geometry in the '%s' layer"),
                    geom.wkbType(), self.name().encode('utf-8'))
            if e: e.tags.update(tags_translation(feature))
        for (key, value) in setup.changeset_tags.items():
            data.tags[key] = value
        if self.source_date:
            data.tags['source:date'] = self.source_date
        log.debug(_("Loaded %d nodes, %d ways, %d relations from '%s' layer"),
            len(data.nodes) - nodes, len(data.ways) - ways,
            len(data.relations) - relations, self.name().encode('utf-8'))
        return data

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
        self.straight_thr = setup.straight_thr # Threshold in degrees from straight angle to delete a vertex
        self.dist_thr = setup.dist_thr # Threshold for topological points.

    @staticmethod
    def get_multipolygon(feature):
        """Returns feature geometry always as a multipolgon"""
        if isinstance(feature, QgsFeature):
            geom = feature.geometry()
        else:
            geom = feature
        if geom.wkbType() == QGis.WKBPolygon:
            return [geom.asPolygon()]
        return geom.asMultiPolygon()

    @staticmethod
    def get_vertices_list(feature):
        """Returns list of all distinct vertices in feature geometry"""
        return [point for part in PolygonLayer.get_multipolygon(feature) \
            for ring in part for point in ring[0:-1]]

    @staticmethod
    def get_outer_vertices(feature):
        """Returns list of all distinct vertices in feature geometry outer rings"""
        return [point for part in PolygonLayer.get_multipolygon(feature) \
            for point in part[0][0:-1]]

    def explode_multi_parts(self, request=QgsFeatureRequest()):
        """
        Creates a new WKBPolygon feature for each part of any WKBMultiPolygon
        feature in request. This avoid relations with may 'outer' members in
        OSM data set. From this moment, localId will not be a unique identifier
        for buildings.
        """
        to_clean = []
        to_add = []
        for feature in self.getFeatures(request):
            geom = feature.geometry()
            if geom.wkbType() == QGis.WKBMultiPolygon:
                for part in geom.asMultiPolygon():
                    feat = QgsFeature(feature)
                    feat.setGeometry(QgsGeometry.fromPolygon(part))
                    to_add.append(feat)
                to_clean.append(feature.id())
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            self.writer.addFeatures(to_add)
            log.debug(_("%d multi-polygons splited into %d polygons in "
                "the '%s' layer"), len(to_clean), len(to_add),
                self.name().encode('utf-8'))

    def get_parents_per_vertex_and_geometries(self):
        """
        Returns:
            (dict) parent fids for each vertex, (dict) geometry for each fid.
        """
        parents_per_vertex = defaultdict(list)
        geometries = {}
        for feature in self.getFeatures():
            geom = QgsGeometry(feature.geometry())
            geometries[feature.id()] = geom
            for point in self.get_vertices_list(feature):
                parents_per_vertex[point].append(feature.id())
        return (parents_per_vertex, geometries)

    def get_parents_per_vertex_and_features(self):
        """
        Returns:
            (dict) parent fids for each vertex, (dict) feature for each fid.
        """
        parents_per_vertex = defaultdict(list)
        features = {}
        for feature in self.getFeatures():
            features[feature.id()] = feature
            for point in self.get_vertices_list(feature):
                parents_per_vertex[point].append(feature.id())
        return (parents_per_vertex, features)

    def get_adjacents_and_geometries(self):
        """
        Returns:
            (list) groups of adjacent polygons
        """
        parents_per_vertex, geometries = self.get_parents_per_vertex_and_geometries()
        adjs = []
        for (point, parents) in parents_per_vertex.items():
            if len(parents) > 1:
                for fid in parents:
                    geom = geometries[fid]
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
        return (groups, geometries)

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

    def clean_duplicated_nodes_in_polygons(self):
        """
        Cleans consecutives nodes with the same coordinates in any ring of a
        polygon.
        """
        dupes = 0
        to_clean = []
        to_change = {}
        for feature in self.getFeatures():
            new_polygon = []
            for part in self.get_multipolygon(feature):
                new_part = []
                for ring in part:
                    if ring:
                        merged = [ring[0]]
                        for i, point in enumerate(ring[1:]):
                            if point == ring[i]:
                                dupes += 1
                            else:
                                merged.append(point)
                        new_part.append(merged)
                new_polygon.append(new_part)
            if dupes:
                if len(new_polygon) > 1:
                    new_geom = QgsGeometry().fromMultiPolygon(new_polygon)
                else:
                    new_geom = QgsGeometry().fromPolygon(new_polygon[0])
                if new_geom and new_geom.isGeosValid():
                    to_change[feature.id()] = new_geom
                else:
                    to_clean.append(feature.id())
        if to_change:
            self.writer.changeGeometryValues(to_change)
            log.debug(_("Merged %d duplicated vertices of polygons in "
                "the '%s' layer"), dupes, self.name().encode('utf-8'))
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d invalid geometries in the '%s' layer"),
                len(to_clean), self.name().encode('utf-8'))

    def topology(self):
        """For each vertex in a polygon layer, adds it to nearest segments."""
        threshold = self.dist_thr # Distance threshold to create nodes
        dup_thr = self.dup_thr
        straight_thr = self.straight_thr
        tp = 0
        td = 0
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_topology.shp", self.crs())
        geometries = {f.id(): QgsGeometry(f.geometry()) for f in self.getFeatures()}
        index = self.get_index()
        to_change = {}
        nodes = set()
        for (gid, geom) in geometries.items():
            for point in frozenset(self.get_outer_vertices(geom)):
                if point not in nodes:
                    area_of_candidates = Point(point).boundingBox(threshold)
                    fids = index.intersects(area_of_candidates)
                    for fid in fids:
                        g = QgsGeometry(geometries[fid])
                        (p, ndx, ndxa, ndxb, dist_v) = g.closestVertex(point)
                        (dist_s, closest, vertex) = g.closestSegmentWithContext(point)
                        note = ""
                        if dist_v == 0:
                            va = g.vertexAt(ndxa)
                            vb = g.vertexAt(ndxb)
                            dist_a = va.sqrDist(point)
                            dist_b = vb.sqrDist(point)
                            if dist_a > 0 and dist_a < dup_thr**2:
                                g.moveVertex(point.x(), point.y(), ndxa)
                                note = "dupe refused by isGeosValid"
                                if g.isGeosValid():
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_a, va.x(), va.y(), point.x(), point.y())
                                    nodes.add(p)
                                    td += 1
                            if dist_b > 0 and dist_b < dup_thr**2:
                                g.moveVertex(point.x(), point.y(), ndxb)
                                note = "dupe refused by isGeosValid"
                                if g.isGeosValid():
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_b, vb.x(), vb.y(), point.x(), point.y())
                                    nodes.add(p)
                                    td += 1
                        elif dist_v < dup_thr**2:
                            g.moveVertex(point.x(), point.y(), ndx)
                            note = "dupe refused by isGeosValid"
                            if g.isGeosValid():
                                note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                    (dist_v, p.x(), p.y(), point.x(), point.y())
                                nodes.add(p)
                                td += 1
                        elif dist_s < threshold**2 and dist_v > 0:
                            va = g.vertexAt(vertex)
                            vb = g.vertexAt(vertex - 1)
                            note = "Topo refused by angle"
                            angle = abs(point.azimuth(va) - point.azimuth(vb))
                            if abs(180 - angle) <= straight_thr:
                                note = "Topo refused by insertVertex"
                                if g.insertVertex(point.x(), point.y(), vertex):
                                    note = "Topo refused by isGeosValid"
                                    if g.isGeosValid():
                                        note = "Add topo %.6f %.5f,%.5f" % \
                                            (dist_s, point.x(), point.y())
                                        tp += 1
                        if note.startswith('Merge') or note.startswith('Add'):
                            to_change[fid] = g
                            geometries[fid] = g
                        if note and log.getEffectiveLevel() <= logging.DEBUG:
                            debshp.add_point(point, note)
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_change)
                to_change = {}
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)
        if td:
            log.debug(_("Merged %d close vertices in the '%s' layer"), td,
                self.name().encode('utf-8'))
        if tp:
            log.debug(_("Created %d topological points in the '%s' layer"),
                tp, self.name().encode('utf-8'))

    def delete_invalid_geometries(self):
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = QgsVectorFileWriter('debug_notvalid.shp', 'UTF-8', QgsFields(),
                QGis.WKBPolygon, self.crs(), 'ESRI Shapefile')
        to_change = {}
        to_clean = []
        rings = 0
        geometries = {feat.id(): QgsGeometry(feat.geometry()) for feat in self.getFeatures()}
        for fid, geom in geometries.items():
            for i, ring in enumerate(geom.asPolygon()):
                n = -1
                while n < 0 or v != QgsPoint(0, 0):
                    n += 1
                    g = QgsGeometry().fromPolygon([ring])
                    f = QgsFeature(QgsFields())
                    f.setGeometry(QgsGeometry(g))
                    v = g.vertexAt(n)
                    (__, is_acute, __, __) = Point(v).get_angle_with_context(g,
                        acute_thr=setup.acute_thr/10.0)
                    if is_acute:
                        g.deleteVertex(n)
                        if not g.isGeosValid() or g.area() < setup.min_area:
                            if i > 0:
                                rings += 1
                                geom.deleteRing(i)
                                to_change[fid] = geom
                                if log.getEffectiveLevel() <= logging.DEBUG:
                                    debshp.addFeature(f)
                            else:
                                to_clean.append(fid)
                                if fid in to_change: del to_change[fid]
                                if log.getEffectiveLevel() <= logging.DEBUG:
                                    debshp.addFeature(f)
                                break
        if to_change:
            self.writer.changeGeometryValues(to_change)
        if rings:
            log.debug(_("Deleted %d invalid ring geometries in the '%s' layer"),
                rings, self.name().encode('utf-8'))
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d invalid geometries in the '%s' layer"),
                len(to_clean), self.name().encode('utf-8'))

    def simplify(self):
        """
        Reduces the number of vertices in a polygon layer according to:

        * Delete vertex if the angle with its adjacents is near of the straight
          angle for less than 'straight_thr' degrees in all its parents.

        * Delete vertex if the distance to the segment formed by its parents is
          less than 'cath_thr' meters.
        """
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_simplify.shp", self.crs())
        killed = 0
        to_change = {}
        # Clean non corners
        (parents_per_vertex, geometries) = self.get_parents_per_vertex_and_geometries()
        for pnt, parents in parents_per_vertex.items():
            # Test if this vertex is a 'corner' in any of its parent polygons
            point = Point(pnt)
            deb_values = []
            for fid in parents:
                geom = geometries[fid]
                (angle, is_acute, is_corner, cath) = point.get_angle_with_context(geom)
                deb_values.append((angle, is_acute, is_corner, cath))
                if is_corner: break
            msg = str(["angle=%.1f, is_acute=%s, is_corner=%s, cath=%.4f" % \
                    v for v in deb_values])
            if not is_corner:
                killed += 1      # delete the vertex from all its parents.
                for fid in frozenset(parents):
                    geom = QgsGeometry(geometries[fid])
                    (__, ndx, __, __, __) = geom.closestVertex(point)
                    geom.deleteVertex(ndx)
                    if geom.isGeosValid():
                        parents.remove(fid)
                        geometries[fid] = geom
                        to_change[fid] = geom
                if log.getEffectiveLevel() <= logging.DEBUG:
                    debshp.add_point(point, "Deleted. %s" % msg)
            elif log.getEffectiveLevel() <= logging.DEBUG:
                debshp.add_point(point, "Keep. %s" % msg)
        if to_change:
            self.writer.changeGeometryValues(to_change)
            log.debug(_("Simplified %d vertices in the '%s' layer"), killed,
                self.name().encode('utf-8'))

    def merge_adjacents(self):
        """Merge polygons with shared segments"""
        (groups, geometries) = self.get_adjacents_and_geometries()
        to_clean = []
        to_change = {}
        for group in groups:
            group = list(group)
            geom = geometries[group[0]]
            for fid in group[1:]:
                geom = geom.combine(geometries[fid])
            to_clean += group[1:]
            to_change[group[0]] = geom
        if to_clean:
            self.writer.changeGeometryValues(to_change)
            self.writer.deleteFeatures(to_clean)
            log.debug(_("%d adjacent polygons merged into %d polygons in the '%s' "
                "layer"), len(to_clean), len(to_change), self.name().encode('utf-8'))

    def clean(self):
        """Merge duplicated vertices and simplify layer"""
        self.topology()
        self.clean_duplicated_nodes_in_polygons()
        self.delete_invalid_geometries()
        self.simplify()


class ParcelLayer(BaseLayer):
    """Class for cadastral parcels"""

    def __init__(self, path="Polygon", baseName="cadastralparcel",
            providerLib="memory", source_date=None):
        super(ParcelLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}
        self.source_date = source_date


class ZoningLayer(PolygonLayer):
    """Class for cadastral zoning"""

    def __init__(self, pattern='{}', path="Polygon", baseName="cadastralzoning",
            providerLib="memory", source_date=None):
        super(ZoningLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
                QgsField('level', QVariant.String, len=254),
                QgsField('levelName', QVariant.String, len=254),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}
        self.source_date = source_date
        self.task_number = 0
        self.task_pattern = pattern

    def get_task(self):
        self.task_number += 1
        return self.task_pattern.format(self.task_number)        

    def append(self, layer, level=None):
        """Append features of layer with levelName 'M' for rustic or 'P' for urban"""
        self.setCrs(layer.crs())
        total = 0
        to_add = []
        multi = 0
        final = 0
        for feature in layer.getFeatures():
            if level == None or level == feature['levelName'][3]:
                feat = self.copy_feature(feature)
                geom = feature.geometry()
                if geom.wkbType() == QGis.WKBMultiPolygon:
                    for part in geom.asMultiPolygon():
                        f = QgsFeature(feat)
                        f.setGeometry(QgsGeometry.fromPolygon(part))
                        to_add.append(f)
                        final += 1
                    multi += 1
                else:
                    to_add.append(feat)
                total += 1
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
        if len(to_add) > 0:
            self.writer.addFeatures(to_add)
        if total:
            log.debug (_("Loaded %d features in '%s' from '%s'"), total,
                self.name().encode('utf-8'), layer.name().encode('utf-8'))
        if multi:
            log.debug(_("%d multi-polygons splited into %d polygons in "
                "the '%s' layer"), multi, final, self.name().encode('utf-8'))

class AddressLayer(BaseLayer):
    """Class for address"""

    def __init__(self, path="Point", baseName="address", providerLib="memory",
            source_date=None):
        super(AddressLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
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
        self.source_date = source_date

    @staticmethod
    def create_shp(name, crs, fields=QgsFields(), geom_type=QGis.WKBPoint):
        QgsVectorFileWriter(name, 'UTF-8', fields, geom_type, crs, 'ESRI Shapefile')

    def to_osm(self, data=None, upload='never'):
        """Export to OSM"""
        return super(AddressLayer, self).to_osm(translate.address_tags, data, upload)

    def conflate(self, current_address):
        """
        Delete address existing in current_address

        Args:
            current_address (OSM): dataset
        """
        to_clean = [feat.id() for feat in self.getFeatures() \
            if feat['TN_text'] + feat['designator'] in current_address]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Refused %d addresses existing in OSM") % len(to_clean))
        to_clean = [feat.id() for feat in self.search("designator = '%s'" \
            % setup.no_number)]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d addresses without house number") % len(to_clean))

    def del_address(self, building_osm):
        """Delete the address if there aren't any associated building."""
        to_clean = []
        building_refs = {el.tags['ref'] for el in building_osm.elements \
            if 'ref' in el.tags}
        for ad in self.getFeatures():
            ref = ad['localId'].split('.')[-1]
            if ref not in building_refs:
                to_clean.append(ad.id())
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.info(_("Deleted %d addresses without associated building"), len(to_clean))

    def get_highway_names(self, highway):
        """
        Returns a dictionary with the translation for each street name.

        Args:
            highway (HighwayLayer): Current OSM highway data

        Returns:
            (dict) highway names translations
        """
        index = highway.get_index()
        features = {feat.id(): feat for feat in highway.getFeatures()}
        highway_names = defaultdict(list)
        for f in self.getFeatures():
            highway_names[f['TN_text']].append(f.geometry().asPoint())
        for name, points in highway_names.items():
            bbox = QgsGeometry().fromMultiPoint(points).boundingBox()
            choices = [features[fid]['name'] for fid in index.intersects(bbox)]
            highway_names[name] = hgwnames.match(name, choices)
        return highway_names


class ConsLayer(PolygonLayer):
    """Class for constructions"""

    def __init__(self, path="Polygon", baseName="building",
            providerLib = "memory", source_date=None):
        super(ConsLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('condition', QVariant.String, len=254),
                QgsField('link', QVariant.String, len=254),
                QgsField('currentUse', QVariant.String, len=254),
                QgsField('bu_units', QVariant.Int),
                QgsField('dwellings', QVariant.Int),
                QgsField('lev_above', QVariant.Int),
                QgsField('lev_below', QVariant.Int),
                QgsField('nature', QVariant.String, len=254),
                QgsField('fixme', QVariant.String, len=254)
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
        self.source_date = source_date

    @staticmethod
    def is_building(feature):
        """Building features have not any underscore in its localId field"""
        return '_' not in feature['localId']

    @staticmethod
    def is_part(feature):
        """Part features have '_part' in its localId field"""
        return '_part' in feature['localId']

    @staticmethod
    def is_pool(feature):
        """Pool features have '_PI.' in its localId field"""
        return '_PI.' in feature['localId']

    @staticmethod
    def merge_adjacent_features(group):
        """Combine all geometries in group of features"""
        geom = group[0].geometry()
        for p in group[1:]:
            geom = geom.combine(p.geometry())
        return geom

    def explode_multi_parts(self, address=False):
        request = QgsFeatureRequest()
        if address:
            refs = {ad['localId'].split('.')[-1] for ad in address.getFeatures()}
            fids = [f.id() for f in self.getFeatures() if f['localId'] not in refs]
            request.setFilterFids(fids)
        super(ConsLayer, self).explode_multi_parts(request)

    def append_zone(self, layer, zone, processed, index):
        """Append features of layer inside zone excluding processed localId's'"""
        self.setCrs(layer.crs())
        fids = index.intersects(zone.geometry().boundingBox())
        request = QgsFeatureRequest().setFilterFids(fids)
        to_add = []
        features = []
        refs = set()
        total = 0
        for feat in layer.getFeatures(request):
            if not feat['localId'] in processed:
                if not '_' in feat['localId'] and is_inside(feat, zone):
                    to_add.append(self.copy_feature(feat))
                    refs.add(feat['localId'])
                    total += 1
                else:
                    features.append(feat)
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
        for feat in features:
            if '_' in feat['localId'] and feat['localId'].split('_')[0] in refs:
                to_add.append(self.copy_feature(feat))
                total += 1
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
        if len(to_add) > 0:
            self.writer.addFeatures(to_add)
        if total > 0:
            log.debug (_("Loaded %d features in '%s' from '%s'"), total,
                self.name().encode('utf-8'), layer.name().encode('utf-8'))
        return refs

    def remove_parts_below_ground(self):
        """Remove all parts with 'lev_above' field equal 0 and 'lev_below' > 0"""
        to_clean = [f.id() for f in self.search('lev_above=0 and lev_below>0')]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d building parts with no floors above ground"),
                len(to_clean))

    def to_osm(self, data=None, upload='never'):
        """Export to OSM"""
        return super(ConsLayer, self).to_osm(translate.building_tags, data, upload)

    def index_of_parts(self):
        """ Index parts of building by building localid. """
        parts = defaultdict(list)
        for part in self.search("regexp_match(localId, '_part')"):
            localId = part['localId'].split('_')[0]
            parts[localId].append(part)
        return parts

    def index_of_building_and_parts(self):
        """
        Constructs some utility dicts.
        buildings index building by localid (call before explode_multi_parts).
        parts index parts of building by building localid.
        """
        buildings = defaultdict(list)
        parts = defaultdict(list)
        for feature in self.getFeatures():
            if self.is_building(feature):
                buildings[feature['localId']].append(feature)
            elif self.is_part(feature):
                localId = feature['localId'].split('_')[0]
                parts[localId].append(feature)
        return (buildings, parts)

    def remove_outside_parts(self):
        """
        Remove parts outside the footprint of it building or without associated
        building.
        Precondition: Called before merge_greatest_part
        """
        to_clean = []
        buildings = {f['localId']: f for f in self.getFeatures() if self.is_building(f)}
        for feat in self.getFeatures():
            if self.is_part(feat):
                ref = feat['localId'].split('_')[0]
                if ref not in buildings:
                    to_clean.append(feat.id())
                else:
                    bu = buildings[ref]
                    if not is_inside(feat, bu):
                        to_clean.append(feat.id())
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Removed %d building parts outside the footprint"), len(to_clean))

    def get_parts(self, footprint, parts):
        """
        Given a building footprint and its parts, for the parts inside the 
        footprint returns a dictionary of parts for levels, the maximum and
        minimum levels
        """
        max_level = 0
        min_level = 0
        parts_for_level = defaultdict(list)
        for part in parts:
            if is_inside(part, footprint):
                level = (part['lev_above'], part['lev_below'])
                if level[0] > max_level: max_level = level[0]
                if level[1] > min_level: min_level = level[1]
                parts_for_level[level].append(part)
        return parts_for_level, max_level, min_level

    def merge_adjacent_parts(self, footprint, parts):
        """
        Given a building footprint and its parts, for the parts inside the 
        footprint:

          * Translates the maximum values of number of levels above and below
            ground to the footprint and deletes all the parts in that level.
          
          * Merges the adjacent parts in the rest of the levels.
        """
        to_clean = []
        to_clean_g = []
        to_change = {}
        to_change_g = {}
        parts_for_level, max_level, min_level = self.get_parts(footprint, parts)
        footprint['lev_above'] = max_level
        footprint['lev_below'] = min_level
        to_change[footprint.id()] = get_attributes(footprint)
        for (level, parts) in parts_for_level.items():
            if level == (max_level, min_level):
                to_clean = [p.id() for p in parts_for_level[max_level, min_level]]
            else:
                geom = self.merge_adjacent_features(parts)
                poly = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
                if len(poly) < len(parts):
                    for (i, part) in enumerate(parts):
                        if i < len(poly):
                            g = QgsGeometry().fromPolygon(poly[i])
                            to_change_g[part.id()] = g
                        else:
                            to_clean_g.append(part.id())
        return to_clean, to_clean_g, to_change, to_change_g

    def merge_building_parts(self):
        """Apply merge_adjacent_parts to each set of building and its parts"""
        parts = self.index_of_parts()
        to_clean = []
        to_clean_g = []
        to_change = {}
        to_change_g = {}
        for building in self.search("not regexp_match(localId, '_')"):
            it_parts = parts[building['localId']]
            cn, cng, ch, chg= self.merge_adjacent_parts(building, it_parts)
            to_clean += cn
            to_clean_g += cng
            to_change.update(ch)
            to_change_g.update(chg)
        if to_clean:
            self.writer.changeAttributeValues(to_change)
            log.debug(_("Translated %d level values to the footprint"), len(to_change))
            self.writer.changeGeometryValues(to_change_g)
            self.writer.deleteFeatures(to_clean + to_clean_g)
            log.debug(_("Merged %d building parts to the footprint"), len(to_clean))
        if to_clean_g:
            log.debug(_("Merged %d adjacent parts"), len(to_clean_g))

    def clean(self):
        """
        Merge duplicated vertices, add topological points, simplify layer
        and merge building parts.
        """
        self.topology()
        self.clean_duplicated_nodes_in_polygons()
        self.delete_invalid_geometries()
        self.merge_building_parts()
        self.simplify()

    def move_address(self, address):
        """
        Move each address to the nearest point in the footprint of its
        associated building (same cadastral reference), but only if:

        * The address specification is Entrance.

        * The new position is enough close and is not a corner
        """
        to_change = {}
        to_move = {}
        to_insert = {}
        (buildings, parts) = self.index_of_building_and_parts()
        for ad in address.getFeatures():
            refcat = ad['localId'].split('.')[-1]
            building_count = len(buildings[refcat])
            if building_count == 1:
                building = buildings[refcat][0]
                it_parts = parts[refcat]
                if ad['spec'] == 'Entrance':
                    point = ad.geometry().asPoint()
                    bg = building.geometry()
                    distance, closest, vertex = bg.closestSegmentWithContext(point)
                    va = bg.vertexAt(vertex - 1)
                    vb = bg.vertexAt(vertex)
                    if distance < setup.addr_thr**2:
                        if closest.sqrDist(va) < setup.entrance_thr**2 \
                                or closest.sqrDist(vb) < setup.entrance_thr**2:
                            ad['spec'] = 'corner'
                            to_change[ad.id()] = get_attributes(ad)
                        else:
                            dg = QgsGeometry.fromPoint(closest)
                            to_move[ad.id()] = dg
                            bg.insertVertex(closest.x(), closest.y(), vertex)
                            to_insert[building.id()] = QgsGeometry(bg)
                            for part in it_parts:
                                pg = part.geometry()
                                for (i, vpa) in enumerate(pg.asPolygon()[0][0:-1]):
                                    vpb = pg.vertexAt(i+1)
                                    if va in (vpa, vpb) and vb in (vpa, vpb):
                                        pg.insertVertex(closest.x(), closest.y(), i+1)
                                        to_insert[part.id()] = QgsGeometry(pg)
                    else:
                        ad['spec'] = 'remote'
                        to_change[ad.id()] = get_attributes(ad)
        address.writer.changeAttributeValues(to_change)
        address.writer.changeGeometryValues(to_move)
        self.writer.changeGeometryValues(to_insert)
        log.debug(_("Moved %d addresses to entrance, %d changed to parcel"),
            len(to_move), len(to_change))

    def validate(self, max_level, min_level):
        """Put fixmes to buildings with not valid geometry, too small or big.
        Returns distribution of floors"""
        to_change = {}
        for feat in self.getFeatures():
            geom = feat.geometry()
            errors = geom.validateGeometry()
            if errors:
                feat['fixme'] = '; '.join([e.what() for e in errors])
                to_change[feat.id()] = get_attributes(feat)
            if ConsLayer.is_building(feat):
                localid = feat['localId']
                if isinstance(feat['lev_above'], int) and feat['lev_above'] > 0:
                    max_level[localid] = feat['lev_above']
                if isinstance(feat['lev_below'], int) and feat['lev_below'] > 0:
                    min_level[localid] = feat['lev_below']
                if feat.id() not in to_change:
                    area = geom.area()
                    if area < setup.warning_min_area:
                        feat['fixme'] = _("Check, area too small")
                        to_change[feat.id()] = get_attributes(feat)
                    if area > setup.warning_max_area:
                        feat['fixme'] = _("Check, area too big")
                        to_change[feat.id()] = get_attributes(feat)
        if to_change:
            self.writer.changeAttributeValues(to_change)

    def conflate(self, current_bu_osm, delete=True):
        """
        Removes from current_bu_osm the buildings that don't have conflicts.
        If delete=False, only mark buildings with conflicts
        """
        index = self.get_index()
        num_buildings = 0
        conflicts = 0
        to_clean = set()
        for el in current_bu_osm.elements:
            poly = None
            if el.type == 'way' and el.is_closed() and 'building' in el.tags:
                poly = [[map(Point, el.geometry())]]
            elif el.type == 'relation' and 'building' in el.tags:
                poly = [[map(Point, w)] for w in el.outer_geometry()]
            if poly:
                num_buildings += 1
                geom = QgsGeometry().fromMultiPolygon(poly)
                if geom.isGeosValid():
                    fids = index.intersects(geom.boundingBox())
                    request = QgsFeatureRequest().setFilterFids(fids)
                    conflict = False
                    for feat in self.getFeatures(request):
                        fg = feat.geometry()
                        if geom.contains(fg) or fg.contains(geom) or geom.overlaps(fg):
                            conflict = True
                            conflicts += 1
                            break
                    if delete and not conflict:
                        to_clean.add(el)
                    if not delete and conflict:
                        el.tags['conflict'] = 'yes'
        for el in to_clean:
            current_bu_osm.remove(el)
        log.debug(_("Detected %d conflicts in %d buildings from OSM"), 
                conflicts, num_buildings)
        return len(to_clean) > 0


class HighwayLayer(BaseLayer):
    """Class for OSM highways"""

    def __init__(self, path="LineString", baseName="highway",
            providerLib="memory"):
        super(HighwayLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
                QgsField('name', QVariant.String, len=254),
            ])
            self.updateFields()
        self.setCrs(QgsCoordinateReferenceSystem(4326))

    def read_from_osm(self, data):
        """Get features from a osm dataset"""
        to_add = []
        for r in data.relations:
            for m in r.members:
                if m.type=='way' and 'name' in r.tags:
                    m.element.tags['name'] = r.tags['name']
        for w in data.ways:
            if 'name' in w.tags:
              points = [QgsPoint(n.x, n.y) for n in w.nodes]
              geom = QgsGeometry.fromPolyline(points)
              feat = QgsFeature(QgsFields(self.pendingFields()))
              feat.setGeometry(geom)
              feat.setAttribute("name", w.tags['name'])
              to_add.append(feat)
        self.writer.addFeatures(to_add)


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

