# -*- coding: utf-8 -*-
"""Application layers"""

import os
import math
import re
from collections import defaultdict
import logging

from qgis.core import *
from PyQt4.QtCore import QVariant

import hgwnames
import osm
import setup
import translate
from report import instance as report
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

    def get_angle(self, geom):
        """
        For the vertex in a geometry nearest to this point, give the angle
        between its adjacent vertexs.

        Args:
            geom (QgsGeometry): Geometry to test.

        Returns:
            (float) Angle between the vertex and their adjacents,
        """
        (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(self)
        va = geom.vertexAt(ndxa) # previous vertex
        vb = geom.vertexAt(ndxb) # next vertex
        angle = abs(point.azimuth(va) - point.azimuth(vb))
        return angle

    def get_corner_context(self, geom, acute_thr=setup.acute_thr,
            straight_thr=setup.straight_thr, cath_thr=setup.dist_thr):
        """
        For the vertex in a geometry nearest to this point, give context to
        determine if it is a corner (the angle differs by more than straight_thr
        of 180 and if the distance from the vertex to the segment formed by
        their adjacents is greater than cath_thr).

        Args:
            geom (QgsGeometry): Geometry to test.
            acute_thr (float): Acute angle threshold.
            straight_thr (float): Straight angle threshold.
            cath_thr (float): Cathetus threshold.

        Returns:
            (float) Angle between the vertex and their adjacents.
            (bool)  True if the angle is too low (< acute_thr).
            (bool)  True for a corner
            (float) Distance from the vertex to the segment formed by their adjacents.
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

    def get_spike_context(self, geom, acute_thr=setup.acute_inv,
            straight_thr=setup.straight_thr, threshold=setup.dist_inv):
        """
        For the vertex in a geometry nearest to this point, give context to
        determine if its a zig-zag or a spike. It's a zig-zag if both the angles
        of this vertex and the closest adjacents are acute. It's a spike if the
        angle of this vertex is acute and the angle of the closest vertex is
        not straight.

        Args:
            geom (QgsGeometry): Geometry to test.
            acute_thr (float): Acute angle threshold.
            straight_thr (float): Straight angle threshold.
            threshold (float): # Filter for angles.

        Returns:
            (float) angle_v = angle between the vertex and their adjacents.
            (float) angle_a = angle between the closest adjacent and their adjacents.
            (int) ndx = index of the vertex
            (int) ndxa = index of the closest adjacent
            (bool) is_acute = True if the angle is too low (< acute_thr).
            (bool) is_zigzag = True if both angle_v and angle_a are acute and
            the distance from va to the segment v-vb is lower than threshold.
            (bool) is_spike = True if is_acute and angle_a is not straight and
            the distance from va to the segment v-vb is lower than threshold.
            (QgsPoint) vx = projection of va over the segment v-vb.
        """
        (v, ndx, ndxa, ndxb, dist) = geom.closestVertex(self)
        va = geom.vertexAt(ndxa) # previous vertex
        vb = geom.vertexAt(ndxb) # next vertex
        angle_v = abs(v.azimuth(va) - v.azimuth(vb))
        is_acute = angle_v < acute_thr if angle_v < 180 else 360 - angle_v < acute_thr
        if not is_acute:
            return angle_v, None, ndx, None, is_acute, False, False, None
        dist_a = math.sqrt(va.sqrDist(v))
        dist_b = math.sqrt(vb.sqrDist(v))
        if dist_a > dist_b: # set va as the closest adjacent
            vc = va
            dist_c = dist_a
            va = vb
            dist_a = dist_b
            ndxa = ndxb
            vb = vc
            dist_b = dist_c
        angle_a = Point(va).get_angle(geom)
        c = abs(math.sin(math.radians(angle_v))) * dist_a
        is_zigzag = angle_a < acute_thr and c < threshold
        is_spike = abs(180 - angle_a) > straight_thr and c < threshold
        if is_zigzag:
            return angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, None
        gamma = abs(90 + angle_v - angle_a)
        dx = abs(dist_a * (math.cos(math.radians(angle_v)) \
            + math.tan(math.radians(gamma)) * math.sin(math.radians(angle_v))))
        x = v.x() + (vb.x() - v.x()) * dx / dist_b
        y = v.y() + (vb.y() - v.y()) * dx / dist_b
        vx = QgsPoint(x, y)
        return angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx


class BaseLayer(QgsVectorLayer):
    """Base class for application layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(BaseLayer, self).__init__(path, baseName, providerLib)
        self.writer = self.dataProvider()
        self.rename={}
        self.resolve={}
        self.reference_matchs={}
        self.keep = False

    @staticmethod
    def create_shp(name, crs, fields=QgsFields(), geom_type=QGis.WKBMultiPolygon):
        writer = QgsVectorFileWriter(name, 'UTF-8', fields, geom_type, crs, 'ESRI Shapefile')
        if writer.hasError() != QgsVectorFileWriter.NoError:
            msg = _("Error when creating shapefile: '%s'") % writer.errorMessage()
            raise IOError(msg)
        return writer

    @staticmethod
    def delete_shp(path):
        QgsVectorFileWriter.deleteShapeFile(path)
        path = os.path.splitext(path)[0] + '.cpg'
        if os.path.exists(path):
            os.remove(path)

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
                self.name(), layer.name())

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
            self.name(), target_crs.description())

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
            log.debug(_("Joined '%s' to '%s'"), source_layer.name(),
                self.name())

    def translate_field(self, field_name, translations, clean=True):
        """
        Transform the values of a field

        Args:
            field_name (str): Name of the field to transform
            translations (dict): A dictionary used to transform field values
            clean (bool): If true (default), delete features without translation
        """
        to_clean = []
        field_ndx = self.pendingFields().fieldNameIndex(field_name)
        if field_ndx >= 0:
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
        if len(to_clean):
            self.writer.deleteFeatures(to_clean)
        return len(to_clean)

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

    def export(self, path, driver_name="ESRI Shapefile", overwrite=True, target_crs_id=None):
        """Write layer to file

        Args:
            path (str): Path of the output file
            driver_name (str): Defaults to ESRI Shapefile.
            overwrite (bool): Defaults to True
            target_crs_id (int): Defaults to source CRS
        """
        if target_crs_id is None:
            target_crs = self.crs() 
        else:
             target_crs = QgsCoordinateReferenceSystem(target_crs_id)
        if os.path.exists(path) and overwrite:
            if driver_name == 'ESRI Shapefile':
                QgsVectorFileWriter.deleteShapeFile(path)
            else:
                os.remove(path)
        return QgsVectorFileWriter.writeAsVectorFormat(self, path, "utf-8",
                target_crs, driver_name) == QgsVectorFileWriter.NoError

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
                msg = _("Detected a %s geometry in the '%s' layer") % \
                    (geom.wkbType(), self.name())
                log.warning(msg)
                report.warnings.add(msg)
            if e: e.tags.update(tags_translation(feature))
        for (key, value) in setup.changeset_tags.items():
            data.tags[key] = value
        if self.source_date:
            data.tags['source:date'] = self.source_date
        log.debug(_("Loaded %d nodes, %d ways, %d relations from '%s' layer"),
            len(data.nodes) - nodes, len(data.ways) - ways,
            len(data.relations) - relations, self.name())
        return data

    def search(self, expression):
        """Returns a features iterator for this search expression"""
        exp = QgsExpression(expression)
        request = QgsFeatureRequest(exp)
        return self.getFeatures(request)

    def count(self, expression):
        """Returns number of features for this search expression"""
        exp = QgsExpression(expression)
        request = QgsFeatureRequest(exp)
        count = 0
        for f in self.getFeatures(request):
            count += 1
        return count


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

    @staticmethod
    def merge_adjacent_features(group):
        """Combine all geometries in group of features"""
        geom = group[0].geometry()
        for p in group[1:]:
            geom = geom.combine(p.geometry())
        return geom

    def get_area(self):
        """Returns total area"""
        return sum([f.geometry().area() for f in self.getFeatures()])
            
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
            log.debug(_("%d multi-polygons splitted into %d polygons in "
                "the '%s' layer"), len(to_clean), len(to_add),
                self.name())
            report.values['multipart_geoms_' + self.name()] = len(to_clean)
            report.values['exploded_parts_' + self.name()] = len(to_add)

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

    def topology(self):
        """For each vertex in a polygon layer, adds it to nearest segments."""
        threshold = self.dist_thr # Distance threshold to create nodes
        dup_thr = self.dup_thr
        straight_thr = self.straight_thr
        tp = 0
        td = 0
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_topology.shp", self)
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
                        va = g.vertexAt(ndxa)
                        vb = g.vertexAt(ndxb)
                        note = ""
                        if dist_v == 0:
                            dist_a = va.sqrDist(point)
                            dist_b = vb.sqrDist(point)
                            if dist_a < dup_thr**2:
                                g.deleteVertex(ndxa)
                                note = "dupe refused by isGeosValid"
                                if g.isGeosValid():
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_a, va.x(), va.y(), point.x(), point.y())
                                    nodes.add(p)
                                    nodes.add(va)
                                    td += 1
                            if dist_b < dup_thr**2:
                                g.deleteVertex(ndxb)
                                note = "dupe refused by isGeosValid"
                                if g.isGeosValid():
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_b, vb.x(), vb.y(), point.x(), point.y())
                                    nodes.add(p)
                                    nodes.add(vb)
                                    td += 1
                        elif dist_v < dup_thr**2:
                            g.moveVertex(point.x(), point.y(), ndx)
                            note = "dupe refused by isGeosValid"
                            if g.isGeosValid():
                                note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                    (dist_v, p.x(), p.y(), point.x(), point.y())
                                nodes.add(p)
                                td += 1
                        elif dist_s < threshold**2 and closest != va and closest != vb:
                            va = g.vertexAt(vertex)
                            vb = g.vertexAt(vertex - 1)
                            angle = abs(point.azimuth(va) - point.azimuth(vb))
                            note = "Topo refused by angle: %.2f" % angle
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
                self.name())
            report.values['vertex_close_' + self.name()] = td
        if tp:
            log.debug(_("Created %d topological points in the '%s' layer"),
                tp, self.name())
            report.values['vertex_topo_' + self.name()] = tp

    def delete_invalid_geometries(self):
        """
        Delete invalid geometries testing if any of it acute angle vertex could
        be deleted. 
        Also removes zig-zag and spike vertex (see Point.get_spike_context).
        """
        if log.getEffectiveLevel() <= logging.DEBUG:
            fpath = os.path.join(os.path.dirname(self.writer.dataSourceUri()), 
                'debug_notvalid.shp')
            debshp = QgsVectorFileWriter(fpath, 'UTF-8', QgsFields(),
                QGis.WKBPolygon, self.crs(), 'ESRI Shapefile')
            debshp2 = DebugWriter("debug_spikes.shp", self)
        to_change = {}
        to_clean = []
        to_move = {}
        rings = 0
        zz = 0
        spikes = 0
        geometries = {f.id(): QgsGeometry(f.geometry()) for f in self.getFeatures()}
        for fid, geom in geometries.items():
            badgeom = False
            for i, ring in enumerate(geom.asPolygon()):
                if badgeom: break
                skip = False
                for n, v in enumerate(ring[0:-1]):
                    angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
                        Point(v).get_spike_context(geom)
                    if skip or not is_acute:
                        skip = False
                        continue
                    g = QgsGeometry().fromPolygon([ring])
                    f = QgsFeature(QgsFields())
                    f.setGeometry(QgsGeometry(g))
                    g.deleteVertex(n)
                    if not g.isGeosValid() or g.area() < setup.min_area:
                        if i > 0:
                            rings += 1
                            geom.deleteRing(i)
                            to_change[fid] = geom
                            geometries[fid] = geom
                            if log.getEffectiveLevel() <= logging.DEBUG:
                                debshp.addFeature(f)
                        else:
                            badgeom = True
                            to_clean.append(fid)
                            if fid in to_change: del to_change[fid]
                            if log.getEffectiveLevel() <= logging.DEBUG:
                                debshp.addFeature(f)
                        break
                    if len(ring) > 4: # (can delete vertexs)
                        va = geom.vertexAt(ndxa)
                        if is_zigzag:
                            g = QgsGeometry(geom)
                            if ndxa > ndx:
                                g.deleteVertex(ndxa)
                                g.deleteVertex(ndx)
                                skip = True
                            else:
                                g.deleteVertex(ndx)
                                g.deleteVertex(ndxa)
                            valid = g.isGeosValid()
                            if valid:
                                geom = g
                                zz += 1
                                to_change[fid] = g
                                geometries[fid] = geom
                            if log.getEffectiveLevel() <= logging.DEBUG:
                                debshp2.add_point(va, 'zza %d %d %d %f' % (fid, ndx, ndxa, angle_a))
                                debshp2.add_point(v, 'zz %d %d %d %s' % (fid, ndx, len(ring), valid))
                        elif is_spike:
                            g = QgsGeometry(geom)
                            to_move[va] = vx #!
                            g.moveVertex(vx.x(), vx.y(), ndxa)
                            g.deleteVertex(ndx)
                            valid = g.isGeosValid()
                            if valid:
                                spikes += 1
                                skip = ndxa > ndx
                                geom = g
                                to_change[fid] = g
                                geometries[fid] = geom
                            if log.getEffectiveLevel() <= logging.DEBUG:
                                debshp2.add_point(vx, 'vx %d %d' % (fid, ndx))
                                debshp2.add_point(va, 'va %d %d %d %f' % (fid, ndx, ndxa, angle_a))
                                debshp2.add_point(v, 'v %d %d %d %s' % (fid, ndx, len(ring), valid))
        if to_move:
            for fid, geom in geometries.items():
                if fid in to_clean: continue
                n = 0
                v = geom.vertexAt(n)
                while v != QgsPoint(0, 0):
                    if v in to_move:
                        g = QgsGeometry(geom)
                        vx = to_move[v]
                        if log.getEffectiveLevel() <= logging.DEBUG:
                            debshp2.add_point(v, 'mv %d %d' % (fid, n))
                            debshp2.add_point(vx, 'mvx %d %d' % (fid, n))
                        g.moveVertex(vx.x(), vx.y(), n)
                        if g.isGeosValid():
                            geom = g
                            to_change[fid] = g
                    n += 1
                    v = geom.vertexAt(n)
        if to_change:
            self.writer.changeGeometryValues(to_change)
        if rings:
            log.debug(_("Deleted %d invalid ring geometries in the '%s' layer"),
                rings, self.name())
            report.values['geom_rings_' + self.name()] = rings
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d invalid geometries in the '%s' layer"),
                len(to_clean), self.name())
            report.values['geom_invalid_' + self.name()] = len(to_clean)
        if zz:
            log.debug(_("Deleted %d zig-zag vertices in the '%s' layer"), zz,
                self.name())
            report.values['vertex_zz_' + self.name()] = zz
        if spikes:
            log.debug(_("Deleted %d spike vertices in the '%s' layer"), spikes,
                self.name())
            report.values['vertex_spike_' + self.name()] = spikes

    def simplify(self):
        """
        Reduces the number of vertices in a polygon layer according to:

        * Delete vertex if the angle with its adjacents is near of the straight
          angle for less than 'straight_thr' degrees in all its parents.

        * Delete vertex if the distance to the segment formed by its parents is
          less than 'cath_thr' meters.
        """
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_simplify.shp", self)
        killed = 0
        to_change = {}
        # Clean non corners
        (parents_per_vertex, geometries) = self.get_parents_per_vertex_and_geometries()
        for pnt, parents in parents_per_vertex.items():
            point = Point(pnt)
            # Test if this vertex is a 'corner' in any of its parent polygons
            for fid in parents:
                geom = geometries[fid]
                (angle, is_acute, is_corner, cath) = point.get_corner_context(geom)
                debmsg = "angle=%.1f, is_acute=%s, is_corner=%s, cath=%.4f" % (angle,
                    is_acute, is_corner, cath)
                if is_corner: break
            msg = "Keep"
            if not is_corner:
                killed += 1      # delete the vertex from all its parents.
                for fid in frozenset(parents):
                    g = QgsGeometry(geometries[fid])
                    (__, ndx, __, __, __) = g.closestVertex(point)
                    (ndxa, ndxb) = g.adjacentVertices(ndx)
                    v = g.vertexAt(ndx)
                    va = g.vertexAt(ndxa)
                    vb = g.vertexAt(ndxb)
                    invalid_ring = (v == va or v == vb or va == vb)
                    g.deleteVertex(ndx)
                    msg = "Refused"
                    if g.isGeosValid() and not invalid_ring:
                        parents.remove(fid)
                        geometries[fid] = g
                        to_change[fid] = g
                        msg = "Deleted"
            if log.getEffectiveLevel() <= logging.DEBUG:
                debshp.add_point(point, msg + ' ' + debmsg)
        if to_change:
            self.writer.changeGeometryValues(to_change)
            log.debug(_("Simplified %d vertices in the '%s' layer"), killed,
                self.name())
            report.values['vertex_simplify_' + self.name()] = killed

    def merge_adjacents(self):
        """Merge polygons with shared segments"""
        (groups, geometries) = self.get_adjacents_and_geometries()
        to_clean = []
        to_change = {}
        count_adj = 0
        count_com = 0
        for group in groups:
            group = list(group)
            count_adj += len(group)
            geom = geometries[group[0]]
            for fid in group[1:]:
                geom = geom.combine(geometries[fid])
            if geom.isMultipart():
                for i, part in enumerate(geom.asMultiPolygon()):
                    g = QgsGeometry.fromPolygon(part)
                    to_change[group[i]] = g
                    count_com += 1
                to_clean += group[i+1:]
            else:
                to_change[group[0]] = geom
                to_clean += group[1:]
                count_com += 1
        if to_clean:
            self.writer.changeGeometryValues(to_change)
            self.writer.deleteFeatures(to_clean)
            log.debug(_("%d adjacent polygons merged into %d polygons in the '%s' "
                "layer"), count_adj, count_com, self.name())

    def difference(self, layer):
        """Calculate the difference of each geometry with those in layer"""
        geometries = {f.id(): QgsGeometry(f.geometry()) for f in layer.getFeatures()}
        index = layer.get_index()
        to_change = {}
        for feat in self.getFeatures():
            g1 = feat.geometry()
            fids = index.intersects(g1.boundingBox())
            for fid in fids:
                g2 = geometries[fid]
                if g2.intersects(g1):
                    g1 = g1.difference(g2)
                    to_change[feat.id()] = g1
        if to_change:
            self.writer.changeGeometryValues(to_change)

    def clean(self):
        """Delete invalid geometries and close vertices, add topological points
        and simplify vertices."""
        self.delete_invalid_geometries()
        self.topology()
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
                QgsField('levelName', QVariant.String, len=254),
                QgsField('zipcode', QVariant.String, len=5),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}
        self.source_date = source_date
        self.task_number = 0
        self.task_pattern = pattern

    def set_tasks(self, zip_code):
        """Assings a unique task label to each zone by overriding splitted 
        multiparts and merged adjacent zones"""
        to_change = {}
        for i, zone in enumerate(self.getFeatures()):
            zone['label'] = self.task_pattern.format(i + 1)
            zone['zipcode'] = zip_code
            attr = get_attributes(zone)
            to_change[zone.id()] = attr
        self.writer.changeAttributeValues(to_change)

    def append(self, layer, level=None):
        """Append features of layer with levelName 'M' for rustic or 'P' for urban"""
        self.setCrs(layer.crs())
        total = 0
        to_add = []
        multi = 0
        final = 0
        for feature in layer.getFeatures():
            if layer.fieldNameIndex('levelName') > 0:
                zone = feature['levelName'][3]
            else:
                zone = feature['LocalisedCharacterString'][0]
            if level == None or level == zone:
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
                self.name(), layer.name())
        if multi:
            log.debug(_("%d multi-polygons splitted into %d polygons in "
                "the '%s' layer"), multi, final, self.name())

    def export_poly(self, filename):
        """Export as polygon file for Osmosis"""
        mun = self.merge_adjacent_features([f for f in self.getFeatures()])
        mun = self.get_multipolygon(mun)
        with open(filename, 'w') as fo:
            fo.write('admin_boundary\n')
            i = 0
            for part in mun:
                for j, ring in enumerate(part):
                    i += 1
                    prefix = '!' if j > 0 else ''
                    fo.write(prefix + str(i) + '\n')
                    for p in ring:
                        fo.write('%f %f\n' % (p.x(), p.y()))
                    fo.write('END\n')
            fo.write('END\n')
        return

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
                QgsField('image', QVariant.String, len=254),
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
            log.debug(_("Refused %d addresses because they exist in OSM") % len(to_clean))
            report.refused_addresses = len(to_clean)
        to_clean = [feat.id() for feat in self.search("designator = '%s'" \
            % setup.no_number)]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d addresses without house number") % len(to_clean))
            report.addresses_without_number = len(to_clean)

    def get_highway_names(self, highway=None):
        """
        Returns a dictionary with the translation for each street name.

        Args:
            highway (HighwayLayer): Current OSM highway data for conflation.
            If highway is None, only parse names.
        Returns:
            (dict) highway names translations
        """
        if highway is None or highway.featureCount() == 0:
            highway_names = {f['TN_text']: hgwnames.parse(f['TN_text']) \
                for f in self.getFeatures()}
        else:
            highway_names = defaultdict(list)
            index = highway.get_index()
            features = {feat.id(): feat for feat in highway.getFeatures()}
            for f in self.getFeatures():
                highway_names[f['TN_text']].append(f.geometry().asPoint())
            for name, points in highway_names.items():
                bbox = QgsGeometry().fromMultiPoint(points).boundingBox()
                choices = [features[fid]['name'] for fid in index.intersects(bbox)]
                highway_names[name] = hgwnames.match(name, choices)
        return highway_names

    def get_image_links(self):
        to_change = {}
        for feat in self.getFeatures():
            url = setup.cadastre_doc_url.format(feat['localId'][-14:])
            feat['image'] = url
            to_change[feat.id()] = get_attributes(feat)
        self.writer.changeAttributeValues(to_change)


class ConsLayer(PolygonLayer):
    """Class for constructions"""

    def __init__(self, path="Polygon", baseName="building",
            providerLib = "memory", source_date=None):
        super(ConsLayer, self).__init__(path, baseName, providerLib)
        if self.pendingFields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('condition', QVariant.String, len=254),
                QgsField('image', QVariant.String, len=254),
                QgsField('currentUse', QVariant.String, len=254),
                QgsField('bu_units', QVariant.Int),
                QgsField('dwellings', QVariant.Int),
                QgsField('lev_above', QVariant.Int),
                QgsField('lev_below', QVariant.Int),
                QgsField('nature', QVariant.String, len=254),
                QgsField('task', QVariant.String, len=254),
                QgsField('fixme', QVariant.String, len=254),
                QgsField('layer', QVariant.Int),
            ])
            self.updateFields()
        self.rename = {
            'condition': 'conditionOfConstruction',
            'image': 'documentLink' ,
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
                self.name(), layer.name())
        return refs

    def set_tasks(self, uzoning, rzoning):
        """Assings to each building and pool the task label of the zone in witch
        it is containd. Parts receives the label of the building it belongs. 
        Parts without associated building are ignored"""
        uindex = uzoning.get_index()
        rindex = rzoning.get_index()
        ufeatures = {f.id(): f for f in uzoning.getFeatures()}
        rfeatures = {f.id(): f for f in rzoning.getFeatures()}
        tasks = {}
        for feat in self.search("not regexp_match(localId, '_part')"):
            if feat['localId'] not in tasks:
                label = None
                fids = uindex.intersects(feat.geometry().boundingBox())
                for fid in fids:
                    zone = ufeatures[fid]
                    if is_inside(feat, zone):
                        label = tasks[feat['localId'].split('_')[0]] = zone['label']
                        break
                if label is None:
                    fids = rindex.intersects(feat.geometry().boundingBox())
                    for fid in fids:
                        zone = rfeatures[fid]
                        if is_inside(feat, zone):
                            label = tasks[feat['localId'].split('_')[0]] = zone['label']
                            break
        del uindex, rindex, ufeatures, rfeatures
        to_change = {}
        for feat in self.getFeatures():
            ref = feat['localId'].split('_')[0]
            if ref in tasks:
                feat['task'] = tasks[ref]
            else:
                feat['fixme'] = _("Missing building footprint for this part")
            to_change[feat.id()] = get_attributes(feat)
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeAttributeValues(to_change)
                to_change = {}
        if len(to_change) > 0:
            self.writer.changeAttributeValues(to_change)

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

    def index_of_pools(self):
        """ Index pools in building parcel by building localid. """
        pools = defaultdict(list)
        for pool in self.search("regexp_match(localId, '_PI')"):
            localId = pool['localId'].split('_')[0]
            pools[localId].append(pool)
        return pools

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
        Remove parts without levels above ground.
        Create footprint for parts without associated building.
        Remove parts outside the footprint of it building.
        Precondition: Called before merge_greatest_part.
        """
        to_clean_o = []
        to_clean_b = []
        to_add = []
        parts_for_ref = defaultdict(list)
        buildings = {f['localId']: f for f in self.getFeatures() if self.is_building(f)}
        for feat in self.getFeatures():
            if self.is_part(feat):
                ref = feat['localId'].split('_')[0]
                if feat['lev_above'] == 0 and feat['lev_below'] != 0:
                    to_clean_b.append(feat.id())
                elif ref not in buildings:
                    parts_for_ref[ref].append(feat)
                else:
                    bu = buildings[ref]
                    if not is_inside(feat, bu):
                        to_clean_o.append(feat.id())
        for ref, parts in parts_for_ref.items():
            feat = QgsFeature(QgsFields(self.pendingFields()))
            feat['localId'] = ref
            geom = self.merge_adjacent_features(parts)
            feat.setGeometry(geom)
            to_add.append(feat)
        if len(to_clean_o) + len(to_clean_b) > 0:
            self.writer.deleteFeatures(to_clean_o + to_clean_b)
        if len(to_clean_o) > 0:
            log.debug(_("Removed %d building parts outside the footprint"), 
                len(to_clean_o))
            report.orphand_parts = len(to_clean_o)
        if len(to_clean_b) > 0:
            log.debug(_("Deleted %d building parts with no floors above ground"),
                len(to_clean_b))
            report.underground_parts = len(to_clean_b)
        if to_add:
            self.writer.addFeatures(to_add)
            log.debug(_("Generated %d building footprints"), len(to_add))
            report.new_footprints = len(to_add)

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
            check_area = False
            for part in parts:
                part_area = round(part.geometry().area(), 0)
                building_area = round(footprint.geometry().area(), 0)
                if part_area > building_area:
                    part['fixme'] = _('This part is bigger than its building')
                    to_change[part.id()] = get_attributes(part)
                    check_area = True
            if check_area:
                continue
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

    def remove_inner_rings(self, feat1, feat2):
        """
        Auxiliary method to remove feat1 or of its inner rings if equals to feat2
        Returns True if feat1 must be deleted and new geometry if any ring is
        removed.
        """
        geom1 = feat1.geometry()
        geom2 = feat2.geometry()
        delete = False
        new_geom = None
        delete_rings = []
        for i, ring in enumerate(geom1.asPolygon()):
            if QgsGeometry().fromPolygon([ring]).equals(geom2):
                if i == 0:
                    delete = True
                    break
                else:
                    delete_rings.append(i)
        if delete_rings:
            poly = [ring for i, ring in enumerate(geom1.asPolygon()) \
                if i not in delete_rings]
            new_geom = QgsGeometry().fromPolygon(poly)
        return delete, new_geom

    def merge_building_parts(self):
        """
        Detect pools contained in a building and assign layer=1.
        Detect buildings/parts with geometry equals to a pool geometry and
        delete them.
        Detect inner rings of buildings/parts with geometry equals to a pool
        geometry and remove them.
        Apply merge_adjacent_parts to each set of building and its parts.
        """
        parts = self.index_of_parts()
        pools = self.index_of_pools()
        to_clean = []
        to_change = {}
        to_change_g = {}
        buildings_in_pools = 0
        levels_to_footprint = 0
        parts_merged_to_building = 0
        adjacent_parts_deleted = 0
        pools_on_roofs = 0
        visited_parcels = set()
        for building in self.search("not regexp_match(localId, '_')"):
            ref = building['localId']
            it_pools = pools[ref]
            it_parts = parts[ref]
            for pool in it_pools:
                if pool['layer'] != 1 and is_inside(pool, building):
                    pool['layer'] = 1
                    to_change[pool.id()] = get_attributes(pool)
                    pools_on_roofs += 1
                del_building, new_geom = self.remove_inner_rings(building, pool)
                if del_building:
                    to_clean.append(building.id())
                    buildings_in_pools += 1
                    break
                if new_geom:
                    to_change_g[building.id()] = QgsGeometry(new_geom)
                if ref not in visited_parcels:
                    for part in frozenset(it_parts):
                        del_part, new_geom = self.remove_inner_rings(part, pool)
                        if del_part:
                            to_clean.append(part.id())
                            it_parts.remove(part)
                            if part in part in parts[ref]:
                                parts[ref].remove(part)
                            adjacent_parts_deleted += 1
                        elif new_geom:
                            to_change_g[part.id()] = QgsGeometry(new_geom)
            visited_parcels.add(ref)
            cn, cng, ch, chg= self.merge_adjacent_parts(building, it_parts)
            to_clean += cn + cng
            to_change.update(ch)
            to_change_g.update(chg)
            levels_to_footprint += len(ch)
            parts_merged_to_building += len(cn)
            adjacent_parts_deleted += len(cng)
        if to_change:
            self.writer.changeAttributeValues(to_change)
        if to_change_g:
            self.writer.changeGeometryValues(to_change_g)
        if to_clean:
            self.writer.deleteFeatures(to_clean)
        if pools_on_roofs:
            log.debug(_("Located %d swimming pools over a building"), pools_on_roofs)
            report.pools_on_roofs = pools_on_roofs
        if buildings_in_pools:
            log.debug(_("Deleted %d buildings coincidents with a swimming pool"),
                buildings_in_pools)
            report.buildings_in_pools = buildings_in_pools
        if levels_to_footprint:
            log.debug(_("Translated %d level values to the footprint"), 
                levels_to_footprint)
        if parts_merged_to_building:
            log.debug(_("Merged %d building parts to the footprint"), 
                parts_merged_to_building)
            report.parts_to_footprint = parts_merged_to_building
        if adjacent_parts_deleted:
            log.debug(_("Merged %d adjacent parts"), adjacent_parts_deleted)
            report.adjacent_parts = adjacent_parts_deleted

    def clean(self):
        """
        Delete invalid geometries and close vertices, add topological points, 
        merge building parts and simplify vertices.
        """
        self.delete_invalid_geometries()
        self.topology()
        self.merge_building_parts()
        self.simplify()

    def move_address(self, address):
        """
        Move each address to the nearest point in the footprint of its
        associated building (same cadastral reference), but only if:

        * The address specification is Entrance.

        * The new position is enough close and is not a corner
        
        Delete the address if the number of associated buildings is not one.
        """
        to_change = {}
        to_move = {}
        to_insert = {}
        to_clean = []
        mp = 0
        oa = 0
        (buildings, parts) = self.index_of_building_and_parts()
        for ad in address.getFeatures():
            refcat = ad['localId'].split('.')[-1]
            building_count = 0 if refcat not in buildings else len(buildings[refcat])
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
                        if vertex > len(bg.asPolygon()[0]):
                            ad['spec'] = 'inner'
                            to_change[ad.id()] = get_attributes(ad)
                        elif closest.sqrDist(va) < setup.entrance_thr**2 \
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
            else:
                to_clean.append(ad.id())
                if building_count == 0:
                    oa += 1
                else:
                    mp += 1
        address.writer.changeAttributeValues(to_change)
        address.writer.changeGeometryValues(to_move)
        self.writer.changeGeometryValues(to_insert)
        log.debug(_("Moved %d addresses to entrance, %d changed to parcel"),
            len(to_move), len(to_change))
        if len(to_clean) > 0:
            address.writer.deleteFeatures(to_clean)
        if oa > 0:
            log.debug(_("Deleted %d addresses without associated building"), oa)
            report.orphand_addresses = oa
        if mp > 0:
            log.debug(_("Refused %d addresses belonging to multiple buildings"), mp)
            report.multiple_addresses = mp

    def validate(self, max_level, min_level):
        """Put fixmes to buildings with not valid geometry, too small or big.
        Returns distribution of floors"""
        to_change = {}
        for feat in self.getFeatures():
            geom = feat.geometry()
            errors = geom.validateGeometry()
            if errors:
                feat['fixme'] = _('GEOS validation') + ': ' + \
                    '; '.join([e.what() for e in errors])
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
        geometries = {f.id(): QgsGeometry(f.geometry()) for f in self.getFeatures()}
        num_buildings = 0
        conflicts = 0
        to_clean = set()
        for el in current_bu_osm.elements:
            poly = None
            is_pool = 'leisure' in el.tags and el.tags['leisure'] == 'swimming_pool'
            is_building = 'building' in el.tags
            if el.type == 'way' and el.is_closed() and (is_building or is_pool):
                poly = [[map(Point, el.geometry())]]
            elif el.type == 'relation' and (is_building or is_pool):
                poly = [[map(Point, w)] for w in el.outer_geometry()]
            if poly:
                num_buildings += 1
                geom = QgsGeometry().fromMultiPolygon(poly)
                if geom is None or not geom.isGeosValid():
                    msg = _("OSM building with id %s is not valid") % el.fid
                    log.warning(msg)
                    report.warnings.append(msg)
                else:
                    fids = index.intersects(geom.boundingBox())
                    conflict = False
                    for fid in fids:
                        fg = geometries[fid]
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
        log.debug(_("Detected %d conflicts in %d buildings/pools from OSM"), 
                conflicts, num_buildings)
        report.osm_buildings = num_buildings
        report.osm_building_conflicts = conflicts
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

    def __init__(self, filename, layer, driver_name="ESRI Shapefile"):
        """
        Args:
            filename (str): File name of the layer
            crs (QgsCoordinateReferenceSystem): Crs of layer.
            driver_name (str): Defaults to ESRI Shapefile.
        """
        fpath = os.path.join(os.path.dirname( \
                layer.dataProvider().dataSourceUri()), filename)
        self.fields = QgsFields()
        self.fields.append(QgsField("note", QVariant.String, len=100))
        QgsVectorFileWriter.__init__(self, fpath, "utf-8", self.fields,
                QGis.WKBPoint, layer.crs(), driver_name)

    def add_point(self, point, note=None):
        """Adds a point to the layer with the attribute note."""
        feat = QgsFeature(QgsFields(self.fields))
        geom = QgsGeometry.fromPoint(point)
        feat.setGeometry(geom)
        if note:
            feat.setAttribute("note", note[:254])
        return self.addFeature(feat)

