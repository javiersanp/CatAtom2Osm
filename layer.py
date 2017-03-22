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
            bool: True for a corner.
            float: Angle between the vertex and their adjacents
            float: Distance from the vertex to the segment formed by their adjacents
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
        
        Kwargs
            rename (dict of dst_attr:src_attr): Translation of attributes names
            resolve (dict of dst_attr:(src_attr, match)): xlink reference fields

        Example:
            With this:
            rename = {'spec': 'specification'}
            resolve = {
                'PD_id': ('component_href', '[\w\.]+PD[\.0-9]+'), 
                'TN_id': ('component_href', '[\w\.]+TN[\.0-9]+'), 
                'AU_id': ('component_href', '[\w\.]+AU[\.0-9]+')
            }
            Yo get:
            original_attributes = ['localId', 'specification', 'component_href']
            original_values = [
                '38.012.1.12.0295603CS6109N', 
                'Parcel', 
                '(3:#ES.SDGC.PD.38.012.38570,#ES.SDGC.TN.38.012.1,#ES.SDGC.AU.38.012)'
            ]
            final_attributes = ['localId', 'spec', 'PD_id', 'TN_id', 'AU_id']
            final_values = [
                '38.012.1.12.0295603CS6109N', 
                'Parcel', 
                'ES.SDGC.PD.38.012.38570',
                'ES.SDGC.TN.38.012.1',
                'ES.SDGC.AU.38.012'
            ]
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
    
    def append(self, layer, rename=None, resolve=None):
        """Copy all features from layer. See copy_feature()"""
        self.setCrs(layer.crs())
        self.startEditing()
        for feature in layer.getFeatures():
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
        Kwargs:
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
        Kwargs:
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


class ZoningLayer(BaseLayer):
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


class AddressLayer(BaseLayer):
    """Clas for address"""

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


class ConsLayer(BaseLayer):
    """Clas for constructions"""

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
                QgsField('nature', QVariant.String, len=254)
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
        self.dup_thr = setup.dup_thr # Distance in meters to merge nearest vertexs.
        self.cath_thr = setup.dist_thr # Threshold in meters for cathetus reduction
        self.angle_thr = setup.angle_thr # Threshold in degrees from straight angle to delete a vertex
        self.dist_thr = setup.dist_thr # Threshold for topological points.

    def explode_multi_parts(self):
        """
        Creates a new WKBPolygon feature for each part of any WKBMultiPolygon 
        feature in the layer. This avoid relations with may 'outer' members in
        OSM data set. From this moment, localId will not be a unique identifier
        for buildings.
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

    @staticmethod
    def is_building(localId):
        """Building features have not any underscore in its localId field"""
        return '_' not in localId

    @staticmethod
    def is_part(localId):
        """Part features have '_part' in its localId field"""
        return '_part' in localId

    def remove_parts_below_ground(self):
        """Remove all parts with 'lev_above' field equal 0."""
        self.startEditing()
        exp = QgsExpression("lev_above=0")
        request = QgsFeatureRequest(exp)
        to_clean = [f.id() for f in self.getFeatures(request)]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
        self.commitChanges()
        return len(to_clean)
        
    def merge_greatest_part(self, footprint, parts):
        """
        Given a building footprint and its parts:
        - Exclude parts not inside the footprint.
        - If the area of the parts above ground is equal to the area of the 
          footprint.
            - Sum the area for all the parts with the same level. Level is the 
              pair of values 'lev_above' and 'lev_below' (number of floors 
              above, and below groud).
            - For the level with greatest area, translate the number of floors 
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
            if self.is_building(feature['localId']):
                buildings[feature['localId']].append(feature.id())
            elif self.is_part(feature['localId']):
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

    def create_dict_of_vertex_and_features(self):
        """
        Auxiliary method for simplify
        Returns:
            vertexs (dict): Dictionary of parent fids for each vertex.
            features (dict): Dictionary of feature for fids.
        """
        vertexs = defaultdict(list)
        features = {}
        for feature in self.getFeatures(): 
            features[feature.id()] = feature
            geom = feature.geometry()
            for ring in geom.asPolygon():
                for point in ring[0:-1]:
                    vertexs[point].append(feature.id())
        return (vertexs, features)

    def simplify(self):
        """
        Reduces the number of vertexs in a polygon layer according to:
        * Merge vertexs nearest than 'dup_thr' meters.
        * Delete vertex if the distance to the segment formed by its parents is
            less than 'cath_thr' meters.
        * Delete vertex if the angle with its parent is near of the straight 
            angle for less than 'angle_thr' degrees.
        """
        dup_thr = self.dup_thr
        cath_thr = self.cath_thr
        angle_thr = self.angle_thr
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_simplify.shp", self.crs())
        index = QgsSpatialIndex()
        index = QgsSpatialIndex(self.getFeatures())
        (vertexs, features) = self.create_dict_of_vertex_and_features()
        killed = 0
        duped = 0
        self.startEditing()
        for pnt, parents in vertexs.items():
            # First, merge vertexs nearest than dup_thr 
            point = Point(pnt)
            area_of_candidates = point.boundingBox(dup_thr)
            for fid in index.intersects(area_of_candidates):
                feat = features[fid]
                geom = feat.geometry()
                (p, ndx, ndxa, ndxb, dist) = geom.closestVertex(point)
                if dist > 0 and dist < dup_thr**2:
                    area = geom.area()
                    if geom.moveVertex(point.x(), point.y(), ndx):
                        duped += 1
                        self.writer.changeGeometryValues({fid: geom})
                        if log.getEffectiveLevel() <= logging.DEBUG:
                            debshp.add_point(point, "Duplicated. dist=%f" % math.sqrt(dist))
            # Test if this vertex is a 'corner' in any of its parent polygons
            corners = 0
            deb_values = []
            for fid in parents:
                feat = features[fid]
                geom = feat.geometry()
                (is_point, angle, cath) = point.is_corner_with_context(geom)
                deb_values.append((is_point, angle, cath))
                if is_point:
                    corners += 1
                    break
            # If not is a corner delete the vertex from all its parents.
            if corners == 0:
                killed += 1
                for fid in parents:
                    feat = features[fid]
                    geom = feat.geometry()
                    (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(point)
                    area = geom.area()
                    if (geom.deleteVertex(ndx)):
                        self.writer.changeGeometryValues({fid: geom})
                if log.getEffectiveLevel() <= logging.DEBUG:
                    debshp.add_point(point, "Deleted. %s" % str(deb_values))
            elif log.getEffectiveLevel() <= logging.DEBUG:
                debshp.add_point(point, "Keep. %s" % str(deb_values))
        self.commitChanges()
        
        if log.getEffectiveLevel() <= logging.DEBUG:
            del debshp
        return (duped, killed)

    def add_topological_points(self):
        """For each vertex in a polygon layer, adds it to nearest segments."""
        threshold = self.dist_thr # Distance threshold to create nodes
        tp = 0
        if log.getEffectiveLevel() <= logging.DEBUG:
            debshp = DebugWriter("debug_topology.shp", self.crs())
        index = QgsSpatialIndex()
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


class DebugWriter(QgsVectorFileWriter):
    """A QgsVectorFileWriter for debugging purposess."""

    def __init__(self, filename, crs, driver_name="ESRI Shapefile"):
        """
        Args:
            filename (str): File name of the layer
            crs (QgsCoordinateReferenceSystem): Crs of layer.
        Kwargs:
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
            feat.setAttribute("note", note)
        return self.addFeature(feat)

