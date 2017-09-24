# -*- coding: utf-8 -*-
import unittest
import mock
import os
import random
from collections import Counter
import logging
logging.disable(logging.WARNING)

import gdal
from qgis.core import *
from PyQt4.QtCore import QVariant

os.environ['LANGUAGE'] = 'C'
import setup
import osm
from layer import *
from catatom2osm import QgsSingleton
qgs = QgsSingleton()


class TestPoint(unittest.TestCase):

    def test_init(self):
        p = Point(1, 2)
        q = Point(p)
        r = Point((1,2))
        self.assertEquals(q.x(), r.x())
        self.assertEquals(q.y(), r.y())

    def test_boundigBox(self):
        radius = random.uniform(0, 100)
        point = Point(random.uniform(0, 100), random.uniform(0, 100))
        r = point.boundingBox(radius)
        self.assertEquals(round(r.center().x()*100), round(point.x()*100))
        self.assertEquals(round(r.center().y()*100), round(point.y()*100))
        self.assertEquals(round(r.width()*100), round(radius*200))
        self.assertEquals(round(r.height()*100), round(radius*200))

    def test_is_corner_with_context(self):
        square = QgsGeometry.fromPolygon([[
            QgsPoint(0, 0),
            QgsPoint(50, 0.6), # dist > 0.5, angle < 5
            QgsPoint(100, 0),
            QgsPoint(105, 50), # dist > 0.5, angle > 5
            QgsPoint(100, 100),
            QgsPoint(2, 100.3), #dist < 0.5, angle > 5
            QgsPoint(0, 100),
            QgsPoint(0.3, 50), #dist < 0.5, angle < 5
            QgsPoint(0, 1),
            QgsPoint(-50, 0), # acute
            QgsPoint(0, 0)
        ]])
        acute_thr = 10
        straight_thr = 5
        cath_thr = 0.5
        (a, is_acute, is_corner, c) = Point(50, 0.4).get_angle_with_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_acute)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(105, 51).get_angle_with_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertTrue(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(5.1, 100).get_angle_with_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(0.4, 50).get_angle_with_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(-51, 0).get_angle_with_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertTrue(is_acute)


class TestBaseLayer(unittest.TestCase):

    def setUp(self):
        self.fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid())
        fn = 'test_layer.shp'
        BaseLayer.create_shp(fn, self.fixture.crs())
        self.layer = PolygonLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid())
        fields1 = []
        fields1.append(QgsField("A", QVariant.String))
        fields1.append(QgsField("B", QVariant.Int))
        self.layer.writer.addAttributes(fields1)
        self.layer.updateFields()

    def tearDown(self):
        QgsVectorFileWriter.deleteShapeFile('test_layer.shp')

    def test_copy_feature_with_resolve(self):
        feature = self.fixture.getFeatures().next()
        resolve = { 'A': ('gml_id', '[0-9]+[A-Z]+[0-9]+[A-Z]') }
        new_fet = self.layer.copy_feature(feature, resolve=resolve)
        self.assertEquals(feature['localId'], new_fet['A'])
        resolve = { 'A': ('gml_id', 'Foo[0-9]+') }
        new_fet = self.layer.copy_feature(feature, resolve=resolve)
        self.assertEquals(new_fet['A'], None)

    def test_copy_feature_with_rename(self):
        feature = self.fixture.getFeatures().next()
        rename = {"A": "gml_id", "B": "value"}
        new_fet = self.layer.copy_feature(feature, rename)
        self.assertEquals(feature['gml_id'], new_fet['A'])
        self.assertEquals(feature['value'], new_fet['B'])
        self.assertTrue(feature.geometry().equals(new_fet.geometry()))

    def test_copy_feature_all_fields(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.startEditing())
        self.assertTrue(layer.isValid())
        feature = self.fixture.getFeatures().next()
        new_fet = layer.copy_feature(feature)
        self.assertTrue(layer.commitChanges())
        self.assertEquals(feature['gml_id'], new_fet['gml_id'])
        self.assertEquals(feature['localId'], new_fet['localId'])
        self.assertTrue(feature.geometry().equals(new_fet.geometry()))

    def test_append_with_rename(self):
        rename = {"A": "gml_id", "B": "value"}
        self.layer.append(self.fixture, rename)
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        feature = self.fixture.getFeatures().next()
        new_fet = self.layer.getFeatures().next()
        self.assertEquals(feature['gml_id'], new_fet['A'])

    def test_append_all_fields(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        feature = self.fixture.getFeatures().next()
        new_fet = layer.getFeatures().next()
        self.assertEquals(feature['gml_id'], new_fet['gml_id'])
        self.assertEquals(feature['localId'], new_fet['localId'])

    def test_append_with_query(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'declined'
        layer.append(self.fixture, query=declined_filter)
        self.assertEquals(layer.featureCount(), 2)

    def test_append_void(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'foobar'
        layer.append(self.fixture, query=declined_filter)
        self.assertEquals(layer.featureCount(), 0)

    def test_add_delete(self):
        feat = QgsFeature(self.layer.pendingFields())
        feat['A'] = 'foobar'
        feat['B'] = 123
        self.assertEquals(self.layer.featureCount(), 0)
        self.layer.writer.addFeatures([feat])
        self.assertEquals(self.layer.featureCount(), 1)
        self.layer.writer.deleteFeatures([feat.id()])
        self.assertEquals(self.layer.featureCount(), 0)

    def test_translate_field(self):
        ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        feat = self.fixture.getFeatures().next()
        geom = QgsGeometry(feat.geometry())
        self.assertTrue(geom.isGeosValid())
        translations = {}
        to_add = []
        for i in range(30):
            feat = QgsFeature(self.layer.pendingFields())
            value = ''.join([random.choice(ascii_uppercase) for j in range(10)])
            translations[value] = value.lower()
            feat['A'] = value
            to_add.append(feat)
        feat = QgsFeature(self.layer.pendingFields())
        feat['A'] = 'FooBar'
        to_add.append(feat)
        self.layer.writer.addFeatures(to_add)
        self.assertGreater(self.layer.featureCount(), 0)
        self.layer.translate_field('TAZ', {})
        self.layer.translate_field('A', translations)
        for feat in self.layer.getFeatures():
            self.assertNotEquals(feat['A'], 'FooBar')
            self.assertEquals(feat['A'], feat['A'].lower())
        self.layer.translate_field('A', translations, clean=False)
        self.assertGreater(self.layer.featureCount(), 0)

    def test_boundig_box(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        self.assertEquals(layer.bounding_box(), None)
        bbox = "28.23518053,-16.45257255,28.23557298,-16.45166103"
        layer.append(self.fixture)
        self.assertEquals(layer.bounding_box(), bbox)

    def test_reproject(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        features_before = layer.featureCount()
        feature_in = layer.getFeatures().next()
        geom_in = feature_in.geometry()
        crs_before = layer.crs()
        layer.reproject()
        feature_out = layer.getFeatures().next()
        self.assertEquals(layer.featureCount(), features_before)
        self.assertEquals(layer.crs(), QgsCoordinateReferenceSystem(4326))
        crs_transform = QgsCoordinateTransform(layer.crs(), crs_before)
        geom_out = feature_out.geometry()
        geom_out.transform(crs_transform)
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEquals(feature_in.attributes(), feature_out.attributes())
        layer.reproject(crs_before)
        feature_out = layer.getFeatures().next()
        geom_out = feature_out.geometry()
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEquals(feature_in.attributes(), feature_out.attributes())

    @mock.patch('layer.QgsSpatialIndex')
    def test_get_index(self, m_index):
        layer = mock.MagicMock()
        layer.test = BaseLayer.get_index.__func__
        layer.featureCount.return_value = 0
        layer.test(layer)
        m_index.assert_called_once_with()
        layer.featureCount.return_value = 1
        layer.test(layer)
        m_index.assert_called_with(layer.getFeatures.return_value)

    @mock.patch('layer.QgsVectorFileWriter')
    @mock.patch('layer.os')
    def test_export_default(self, mock_os, mock_fw):
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        mock_fw.writeAsVectorFormat.return_value = QgsVectorFileWriter.NoError
        mock_fw.NoError = QgsVectorFileWriter.NoError
        self.assertTrue(self.layer.export('foobar'))
        mock_fw.deleteShapeFile.assert_called_once_with('foobar')
        mock_fw.writeAsVectorFormat.assert_called_once_with(self.layer, 'foobar',
            'utf-8', self.layer.crs(), 'ESRI Shapefile')

    @mock.patch('layer.QgsVectorFileWriter')
    @mock.patch('layer.os')
    def test_export_other(self, mock_os, mock_fw):
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        self.layer.export('foobar', 'foo')
        mock_os.remove.assert_called_once_with('foobar')
        self.layer.export('foobar', 'foo', overwrite=False)
        mock_os.remove.assert_called_once_with('foobar')


class TestPolygonLayer(unittest.TestCase):

    def setUp(self):
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'test_layer.shp'
        PolygonLayer.create_shp(fn, self.fixture.crs())
        self.layer = PolygonLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename='')
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        QgsVectorFileWriter.deleteShapeFile('test_layer.shp')

    def test_get_multipolygon(self):
        p = [[QgsPoint(0,0), QgsPoint(1,0), QgsPoint(1,1), QgsPoint(0,0)]]
        mp = [[[QgsPoint(2,0), QgsPoint(3,0), QgsPoint(3,1), QgsPoint(2,0)]], p]
        f = QgsFeature(QgsFields())
        f.setGeometry(QgsGeometry().fromPolygon(p))
        self.assertEquals(PolygonLayer.get_multipolygon(f), [p])
        f.setGeometry(QgsGeometry().fromMultiPolygon(mp))
        self.assertEquals(PolygonLayer.get_multipolygon(f), mp)

    def test_get_vertices_list(self):
        p = [[QgsPoint(0,0), QgsPoint(1,0), QgsPoint(1,1), QgsPoint(0,0)]]
        mp = [[[QgsPoint(2,0), QgsPoint(3,0), QgsPoint(3,1), QgsPoint(2,0)]], p]
        f = QgsFeature(QgsFields())
        f.setGeometry(QgsGeometry().fromMultiPolygon(mp))
        v = [mp[0][0][0], mp[0][0][1], mp[0][0][2], p[0][0], p[0][1], p[0][2]]
        self.assertEquals(PolygonLayer.get_vertices_list(f), v)

    def test_get_outer_vertices(self):
        p1 = [QgsPoint(1,1), QgsPoint(2,1), QgsPoint(2,2), QgsPoint(1,1)]
        p2 = [QgsPoint(0,0), QgsPoint(3,0), QgsPoint(3,3), QgsPoint(0,0)]
        p3 = [QgsPoint(4,0), QgsPoint(5,0), QgsPoint(5,1), QgsPoint(4,0)]
        mp = [[p1, p2], [p3]]
        f = QgsFeature(QgsFields())
        f.setGeometry(QgsGeometry().fromMultiPolygon(mp))
        v = p1[:-1] + p3[:-1]
        self.assertEquals(PolygonLayer.get_outer_vertices(f), v)

    def test_explode_multi_parts(self):
        mp = [f for f in self.layer.getFeatures()
            if f.geometry().isMultipart()]
        self.assertGreater(len(mp), 0, "There are multipart features")
        features_before = self.layer.featureCount()
        request = QgsFeatureRequest()
        request.setFilterFid(mp[0].id())
        nparts = len(mp[0].geometry().asMultiPolygon())
        self.layer.explode_multi_parts(request)
        self.assertEquals(features_before + nparts - 1, self.layer.featureCount())
        nparts = sum([len(f.geometry().asMultiPolygon()) for f in mp])
        self.assertGreater(nparts, len(mp), "With more than one part")
        self.assertTrue(nparts > 1, "Find a multipart feature")
        self.layer.explode_multi_parts()
        m = "After exploding there must be more features than before"
        self.assertGreater(self.layer.featureCount(), features_before, m)
        m = "Number of features before plus number of parts minus multiparts " \
            "equals actual number of features"
        self.assertEquals(features_before + nparts - len(mp),
            self.layer.featureCount(), m)
        m = "Parts must be single polygons"
        self.assertTrue(all([not f.geometry().isMultipart()
            for f in self.layer.getFeatures()]), m)

    def test_get_parents_per_vertex_and_features(self):
        (parents_per_vertex, features) = self.layer.get_parents_per_vertex_and_features()
        self.assertEquals(len(features), self.layer.featureCount())
        self.assertTrue(all([features[fid].id() == fid for fid in features]))
        self.assertGreater(len(parents_per_vertex), 0)
        self.assertTrue(all([QgsGeometry().fromPoint(vertex) \
            .intersects(features[fid].geometry())
                for (vertex, fids) in parents_per_vertex.items() for fid in fids]))

    def test_get_vertices(self):
        vertices = self.layer.get_vertices()
        vcount = 0
        for feature in self.layer.getFeatures():
            for part in PolygonLayer.get_multipolygon(feature):
                for ring in part:
                    for point in ring[0:-1]:
                        vcount += 1
        self.assertEquals(vcount, vertices.featureCount())

    def test_get_duplicates(self):
        duplicates = self.layer.get_duplicates()
        self.assertGreater(len(duplicates), 0)
        distances = [point.sqrDist(dup) for point, dupes in duplicates.items()
            for dup in dupes]
        self.assertTrue(all([dist < setup.dup_thr for dist in distances]))

    def test_merge_duplicates(self):
        duplicates = self.layer.get_duplicates()
        self.assertGreater(len(duplicates), 0)
        self.layer.merge_duplicates()
        duplicates = self.layer.get_duplicates()
        self.assertEquals(len(duplicates), 0)

    def test_clean_duplicated_nodes_in_polygons(self):
        features = self.layer.getFeatures()
        feat1 = features.next()
        geom1 = feat1.geometry()
        new_geom1 = QgsGeometry(geom1)
        l = len(new_geom1.asPolygon()[0])
        self.assertGreater(l, 3)
        v = new_geom1.vertexAt(l-1)
        self.assertTrue(new_geom1.insertVertex(v.x(), v.y(), l-1))
        v = new_geom1.vertexAt(0)
        self.assertTrue(new_geom1.insertVertex(v.x(), v.y(), 0))
        v = new_geom1.vertexAt(l/2)
        self.assertTrue(new_geom1.insertVertex(v.x(), v.y(), l/2))
        self.assertTrue(new_geom1.insertVertex(v.x(), v.y(), l/2))
        feat2 = features.next()
        geom2 = feat2.geometry()
        self.assertGreater(len(geom2.asPolygon()[0]), 2)
        v1 = geom2.vertexAt(0)
        v2 = geom2.vertexAt(1)
        new_geom2 = QgsGeometry().fromPolygon([[v1, v2, v2, v1]])
        feat3 = features.next()
        geom3 = feat3.geometry()
        self.layer.writer.changeGeometryValues({feat1.id(): new_geom1})
        self.layer.writer.changeGeometryValues({feat2.id(): new_geom2})
        self.layer.clean_duplicated_nodes_in_polygons()
        features = self.layer.getFeatures()
        new_feat = features.next()
        self.assertTrue(geom1.equals(new_feat.geometry()))
        new_feat = features.next()
        self.assertTrue(geom3.equals(new_feat.geometry()))


class TestParcelLayer(unittest.TestCase):

    def test_init(self):
        layer = ParcelLayer()
        self.assertEquals(layer.pendingFields()[0].name(), 'localId')
        self.assertEquals(layer.pendingFields()[1].name(), 'label')
        self.assertEquals(layer.rename['localId'], 'inspireId_localId')

    def test_not_empty(self):
        layer = ParcelLayer('test/building.gml', 'building', 'ogr')
        self.assertEquals(len(layer.pendingFields().toList()), 23)


class TestZoningLayer(unittest.TestCase):

    def setUp(self):
        self.fixture = QgsVectorLayer('test/zoning.gml', 'zoning', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        self.layer = ZoningLayer()
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture)
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        self.layer.explode_multi_parts()

    def test_get_adjacents_and_features(self):
        (groups, features) = self.layer.get_adjacents_and_features()
        self.assertTrue(all([len(g) > 1 for g in groups]))
        for group in groups:
            for other in groups:
                if group != other:
                    self.assertTrue(all(p not in other for p in group))

    def test_merge_adjacents(self):
        self.layer.merge_adjacents()
        (groups, features) = self.layer.get_adjacents_and_features()
        self.assertEquals(len(groups), 0)

    def test_append(self):
        layer1 = ZoningLayer()
        layer1.append(self.fixture, 'M')
        layer2 = ZoningLayer()
        layer2.append(self.fixture, 'P')
        self.assertEquals(layer1.featureCount() + layer2.featureCount(),
            self.fixture.featureCount())
        for f in layer1.getFeatures():
            self.assertEquals(f['levelName'][3], 'M')
        for f in layer2.getFeatures():
            self.assertEquals(f['levelName'][3], 'P')
        exp = QgsExpression("localId = '69297CS5262N'")
        request = QgsFeatureRequest(exp)
        f = layer1.getFeatures(request).next()
        g = f.geometry()
        self.assertTrue(g.isMultipart())


class TestConsLayer(unittest.TestCase):

    def setUp(self):
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'test_layer.shp'
        ConsLayer.create_shp(fn, self.fixture.crs())
        self.layer = ConsLayer(fn, 'zoning', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename='')
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        QgsVectorFileWriter.deleteShapeFile('test_layer.shp')

    def test_is_building(self):
        self.assertTrue(ConsLayer.is_building({'localId': 'foobar'}))
        self.assertFalse(ConsLayer.is_building({'localId': 'foo_bar'}))

    def test_is_part(self):
        self.assertTrue(ConsLayer.is_part({'localId': 'foo_part1'}))
        self.assertFalse(ConsLayer.is_part({'localId': 'foo_PI.1'}))

    def test_is_pool(self):
        self.assertTrue(ConsLayer.is_pool({'localId': 'foo_PI.1'}))
        self.assertFalse(ConsLayer.is_pool({'localId': 'foo_part1'}))

    def test_merge_adjacent_features(self):
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        geom = self.layer.merge_adjacent_features(parts)
        area = sum([p.geometry().area() for p in parts])
        self.assertEquals(100*round(geom.area(), 2), 100*round(area, 2))
        self.assertGreater(len(geom.asMultiPolygon()), 0)
        self.assertLess(len(geom.asMultiPolygon()), len(parts))

    def test_explode_multi_parts(self):
        mp0 = [f for f in self.layer.getFeatures()
            if f.geometry().isMultipart()]
        self.assertGreater(mp0, 0)
        address = AddressLayer()
        address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        address.append(address_gml)
        refs = {ad['localId'].split('.')[-1] for ad in address.getFeatures()}
        mp1 = [f for f in self.layer.getFeatures() if f['localId'] in refs and
            f.geometry().isMultipart()]
        self.assertGreater(mp1, 0)
        self.layer.explode_multi_parts(address)
        mp2 = [f for f in self.layer.getFeatures()
            if f.geometry().isMultipart()]
        self.assertEquals(len(mp1), len(mp2))

    def test_append_building(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = fixture.getFeatures().next()
        new_fet = layer.getFeatures().next()
        self.assertEquals(feature['conditionOfConstruction'], new_fet['condition'])
        self.assertEquals(feature['localId'], new_fet['localId'])

    def test_append_buildingpart(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/buildingpart.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = fixture.getFeatures().next()
        new_fet = layer.getFeatures().next()
        self.assertEquals(feature['numberOfFloorsAboveGround'], new_fet['lev_above'])
        self.assertEquals(feature['localId'], new_fet['localId'])

    def test_append_othercons(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/othercons.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = fixture.getFeatures().next()
        new_fet = layer.getFeatures().next()
        self.assertEquals(feature['constructionNature'], new_fet['nature'])
        self.assertEquals(feature['localId'], new_fet['localId'])

    def test_append_cons(self):
        exp = QgsExpression("nature = 'openAirPool'")
        request = QgsFeatureRequest(exp)
        feat = self.layer.getFeatures(request).next()
        self.assertNotEquals(feat, None)
        layer = ConsLayer()
        layer.rename = {}
        layer.append(self.layer)
        feat = layer.getFeatures(request).next()
        self.assertNotEquals(feat, None)

    def test_append_zone(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        index = QgsSpatialIndex(fixture.getFeatures())
        poly = [(357485.75, 3124157.86), (357483.21, 3124119.41), (357512.30,
            3124116.16), (357514.54, 3124154.81), (357485.75, 3124157.86)]
        geom = QgsGeometry().fromPolygon([[QgsPoint(p[0], p[1]) for p in poly]])
        zone = QgsFeature(self.layer.pendingFields())
        zone.setGeometry(geom)
        layer.append_zone(fixture, zone, [], index)
        self.assertEquals(layer.featureCount(), 4)
        processed = ['7541401CS5274S', '7541412CS5274S', '7541413CS5274S',
            '7541415CS5274S']
        for f in layer.getFeatures():
            self.assertIn(f['localId'], processed)
        layer = ConsLayer()
        layer.append_zone(fixture, zone, processed, index)
        self.assertEquals(layer.featureCount(), 0)

    def test_append_task(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/buildingpart.gml', 'part', 'ogr')
        self.assertTrue(fixture.isValid())
        processed = ['7541401CS5274S', '7541412CS5274S', '7541413CS5274S',
            '7541415CS5274S']
        layer.append_task(fixture, processed)
        self.assertEquals(layer.featureCount(), 5)

    def test_remove_parts_below_ground(self):
        to_clean = [f.id() for f in self.layer.search('lev_above=0 and lev_below>0')]
        self.assertGreater(len(to_clean), 0, 'There are parts below ground')
        self.layer.remove_parts_below_ground()
        to_clean = [f.id() for f in self.layer.search('lev_above=0 and lev_below>0')]
        self.assertEquals(len(to_clean), 0, 'There are not parts below ground')

    def test_index_of_building_and_parts(self):
        (buildings, parts) = self.layer.index_of_building_and_parts()
        b = [f for f in self.layer.getFeatures() if self.layer.is_building(f)]
        p = [f for f in self.layer.getFeatures() if self.layer.is_part(f)]
        self.assertEqual(sum(len(g) for g in buildings.values()), len(b))
        self.assertEqual(sum(len(g) for g in parts.values()), len(p))
        self.assertTrue(all([localid==bu['localid']
            for (localid, group) in buildings.items() for bu in group]))
        self.assertTrue(all([localid==pa['localid'][0:14]
            for (localid, group) in parts.items() for pa in group]))

    def test_remove_outside_parts(self):
        refs = [
            '000902900CS52D_part1',
            '8742721CS5284S_part10',
            '8742721CS5284S_part5',
            '8742708CS5284S_part1',
            '8742707CS5284S_part2',
            '8742707CS5284S_part6'
        ]
        self.layer.remove_outside_parts()
        for feat in self.layer.getFeatures():
            self.assertNotIn(feat['localId'], refs)

    def test_get_parts(self):
        self.layer.explode_multi_parts()
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        for footprint in self.layer.search("localId = '8840501CS5284S'"):
            parts_inside = [p for p in parts if is_inside(p, footprint)]
            parts_for_level, max_level, min_level = self.layer.get_parts(footprint, parts)
            max_levelc = max([p['lev_above'] for p in parts_inside])
            min_levelc = max([p['lev_below'] for p in parts_inside])
            self.assertEquals(len(parts_inside), sum([len(p) for p in parts_for_level.values()]))
            for part in parts_inside:
                self.assertIn(part, parts_for_level[(part['lev_above'], part['lev_below'])]) 
            self.assertEquals(max_level, max_levelc)
            self.assertEquals(min_level, min_levelc)

    def test_merge_adjacent_parts(self, ref=None):
        if ref == None:
            self.layer.explode_multi_parts()
            ref = '8842323CS5284S'
        parts = [p for p in self.layer.search("localId like '%s_part%%'" % ref)]
        for footprint in self.layer.search("localId = '%s'" % ref):
            cn, cng, ch, chg= self.layer.merge_adjacent_parts(footprint, parts)
            parts_for_level, max_level, min_level = self.layer.get_parts(footprint, parts)
            if len(parts_for_level) > 1:
                areap = 0
                for level, group in parts_for_level.items():
                    geom = ConsLayer.merge_adjacent_features(group)
                    poly = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
                    if len(poly) < len(group):
                        areap += geom.area()
                aream = sum([g.area() for g in chg.values()])
                self.assertEquals(100*round(areap, 2), 100*round(aream, 2))
            self.assertEquals(max([l[0] for l in parts_for_level.keys()]), max_level)
            self.assertEquals(max([l[1] for l in parts_for_level.keys()]), min_level)
            self.assertEquals(ch[footprint.id()][6], max_level)
            self.assertEquals(ch[footprint.id()][7], min_level)
            self.assertEquals(set(cn), set([p.id() for p in parts_for_level[max_level, min_level]]))

    def test_merge_building_parts(self):
        self.layer.remove_parts_below_ground()
        self.layer.merge_building_parts()
        for ref in self.layer.getFeatures():
            if self.layer.is_building(ref):
                self.test_merge_adjacent_parts(ref)

    def test_add_topological_points(self):
        refs = [
            ('8842708CS5284S', QgsPoint(358821.08, 3124205.68), 0),
            ('8842708CS5284S_part1', QgsPoint(358821.08, 3124205.68), 0),
            ('8942325CS5284S', QgsPoint(358789.2925, 3124247.643), 0),
            ('8942325CS5284S_part1', QgsPoint(358789.2925, 3124247.643), 0),
            ('8942328CS5284S', QgsPoint(358857.04, 3124248.6705), 1),
            ('8942328CS5284S_part3', QgsPoint(358857.04, 3124248.6705), 0)
        ]
        for ref in refs:
            building = self.layer.search("localId = '%s'" % ref[0]).next()
            poly = PolygonLayer.get_multipolygon(building)
            self.assertNotIn(ref[1], poly[ref[2]][0])
        self.layer.add_topological_points()
        for ref in refs:
            building = self.layer.search("localId = '%s'" % ref[0]).next()
            poly = PolygonLayer.get_multipolygon(building)
            self.assertIn(ref[1], poly[ref[2]][0])

    def test_simplify1(self):
        refs = [
            ('8643326CS5284S', QgsPoint(358684.62, 3124377.54), True),
            ('8643326CS5284S', QgsPoint(358686.29, 3124376.11), True),
            ('8643324CS5284S', QgsPoint(358677.29, 3124366.64), False),
        ]
        self.layer.explode_multi_parts()
        self.layer.simplify()
        for ref in refs:
            building = self.layer.search("localId = '%s'" % ref[0]).next()
            self.assertEquals(ref[1] in building.geometry().asPolygon()[0], ref[2])

    def test_simplify2(self):
        layer = ConsLayer()
        writer = layer.dataProvider()
        fixture1 = QgsVectorLayer('test/38023.buildingpart.gml', 'building', 'ogr')
        self.assertTrue(fixture1.isValid(), "Loading fixture")
        layer.append(fixture1, rename='')
        self.assertEquals(layer.featureCount(), fixture1.featureCount())
        fixture2 = QgsVectorLayer('test/38023.buildingpart.gml', 'buildingpart', 'ogr')
        self.assertTrue(fixture2.isValid(), "Loading fixture")
        layer.append(fixture2, rename='')
        self.assertEquals(layer.featureCount(), fixture1.featureCount() + fixture2.featureCount())
        layer.explode_multi_parts()
        layer.remove_parts_below_ground()
        layer.merge_duplicates()
        layer.clean_duplicated_nodes_in_polygons()
        layer.add_topological_points()
        layer.simplify()
        for feat in layer.getFeatures():
            geom = feat.geometry()
            self.assertTrue(geom.isGeosValid(), feat['localId'])
        layer.merge_building_parts()

    def test_move_address(self):
        refs = {
            '38.012.10.10.8643403CS5284S': 'Entrance',
            '38.012.10.11.8842304CS5284S': 'Entrance',
            '38.012.10.13.8842305CS5284S': 'Entrance',
            '38.012.10.14.8643404CS5284S': 'corner',
            '38.012.10.14.8643406CS5284S': 'Parcel',
            '38.012.10.2.8642321CS5284S': 'Entrance',
            '38.012.15.73.8544911CS5284S': 'remote'
        }
        address = AddressLayer()
        address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        address.append(address_gml)
        self.layer.move_address(address)
        self.assertEquals(address.featureCount(), 14)
        for ad in address.getFeatures():
            if ad['localId'] in refs.keys():
                self.assertEquals(ad['spec'], refs[ad['localId']])
                if ad['spec'] == 'Entrance':
                    refcat = ad['localId'].split('.')[-1]
                    building = self.layer.search("localId = '%s'" % refcat).next()
                    self.assertTrue(ad.geometry().touches(building.geometry()))

    def test_check_levels_and_area(self):
        self.layer.merge_building_parts()
        min_level = {}
        max_level = {}
        refs = ['7239208CS5273N', '38012A00400007']
        self.layer.check_levels_and_area(min_level, max_level)
        for (l, v) in {1: 126, 2: 114, 3: 67, 4: 16, 5: 1}.items():
            self.assertEquals(Counter(max_level.values())[l], v)
        for (l, v) in {1: 68, 2: 2}.items():
            self.assertEquals(Counter(min_level.values())[l], v)
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = self.layer.getFeatures(request).next()
            self.assertNotEquals(feat['fixme'], '')
    
    def test_to_osm(self):
        data = self.layer.to_osm(upload='always')
        self.assertEquals(data.upload, 'always')
        ways = 0
        rels = 0
        c = Counter()
        for feat in self.layer.getFeatures():
            g = feat.geometry()
            if g.wkbType() == QGis.WKBPolygon:
                p = g.asPolygon()
                ways += len(p)
                rels += (1 if len(p) > 1 else 0)
            else:
                p = g.asMultiPolygon()
                ways += sum([len(s) for s in p])
                rels += (1 if len(p) > 1 else 0)
        self.assertEquals(ways, len(data.ways))
        self.assertEquals(rels, len(data.relations))

    def test_conflate(self):
        self.layer.reproject()
        d = osm.Osm()
        d.Way(((-16.44211325828, 28.23715394977), (-16.44208978895, 28.23714124855),
            (-16.44209884141, 28.23712884271), (-16.44212197546, 28.23714361157),
            (-16.44211325828, 28.23715394977)), dict(building='yes', ref='1'))
        d.Way(((-16.44016295806, 28.23657619128), (-16.43985450402, 28.23641077902),
            (-16.43991753593, 28.23632689127), (-16.44020855561, 28.23648403305),
            (-16.44016295806, 28.23657619128)), dict(building='yes', ref='2'))
        d.Way(((-16.44051231511, 28.23655551417), (-16.44042112, 28.23650529975),
            (-16.4405699826, 28.23631153095), (-16.44065782495, 28.23635288407),
            (-16.44051231511, 28.23655551417)), dict(building='yes', ref='3'))
        self.assertEquals(len(d.ways), 3)
        self.layer.conflate(d, delete=False)
        self.assertEquals(len(d.ways), 3)
        for el in d.ways:
            self.assertEquals('conflict' in el.tags, el.tags['ref'] == '3')
        d.Way(((-16.44038491018, 28.23645095), (-16.44029706784, 28.23640132629),
            (-16.44042514332, 28.23624713819), (-16.44049689241, 28.23629558045),
            (-16.44038491018, 28.23645095)), dict(building='yes', ref='4'))
        d.Way(((-16.44019514591, 28.23634461522), (-16.44002616674, 28.23625009376),
            (-16.44011199743, 28.23611540052), (-16.44027829438, 28.23619810692)),
            dict(building='yes', ref='5'))
        d.Way(((-16.43993497163, 28.23591926797), (-16.43972575933, 28.23580584175),
            (-16.4398062256, 28.23610122228), (-16.43959701329, 28.23598543321),
            (-16.43993497163, 28.23591926797)), dict(building='yes', ref='6'))
        d.Way(((-16.4386775, 28.2360472), (-16.4386158, 28.2363235),
            (-16.4384536, 28.2362954), (-16.4385153, 28.2360191),
            (-16.4386775, 28.2360472)), dict(building='yes', ref='7'))
        d.Way(((-16.4386049, 28.2357006), (-16.4385316, 28.2356401),
            (-16.4385093, 28.2356419), (-16.4384993, 28.2357054),
            (-16.4386049, 28.2357006)), dict(building='yes', ref='8'))
        w0 = d.Way(((-16.4409784, 28.2365733), (-16.4409231, 28.236542),
            (-16.4409179, 28.2365154), (-16.4409268, 28.236504),
            (-16.4408588, 28.236465)))
        w1 = d.Way(((-16.4406755, 28.236688), (-16.4408332, 28.2367735)))
        w2 = d.Way(((-16.4408332, 28.2367735), (-16.4408943, 28.2366893),
            (-16.4409395, 28.2367147), (-16.4409818, 28.2366563),
            (-16.4409366, 28.2366308), (-16.4409784, 28.2365733)))
        w3 = d.Way(((-16.4408588, 28.236465), (-16.4408086, 28.2365319),
            (-16.4407037, 28.2364709), (-16.4406669, 28.2365102),
            (-16.4406513, 28.2365338), (-16.440639, 28.2365663),
            (-16.4407394, 28.2366223), (-16.4407188, 28.2366474),
            (-16.440707, 28.2366405), (-16.4406755, 28.236688)))
        w4 = d.Way(((-16.440072, 28.236560), (-16.439966, 28.236505),
            (-16.439888, 28.236605), (-16.4399860, 28.236666),
            (-16.440072, 28.236560)))
        w5 = d.Way(((-16.439965, 28.236703), (-16.439861, 28.236642),
            (-16.439805, 28.236733), (-16.439903, 28.236790),
            (-16.439965, 28.236703)))
        r1 = d.Relation(tags = dict(building='yes', ref='9'))
        r1.append(w0, 'outer')
        r1.append(w1, 'outer')
        r1.append(w2, 'outer')
        r1.append(w3, 'outer')
        r2 = d.Relation  (tags = dict(building='yes', ref='10'))
        r2.append(w4, 'outer')
        r2.append(w5, 'outer')
        self.assertEquals(len(d.ways), 14)
        self.assertEquals(len(d.relations), 2)
        self.layer.conflate(d)
        self.assertEquals(len(d.ways), 12)
        self.assertEquals(len(d.relations), 2)
        self.assertEquals({e.tags['ref'] for e in d.ways if 'ref' in e.tags},
            {'3', '4', '5', '6', '7', '8'})


class TestAddressLayer(unittest.TestCase):

    def setUp(self):
        self.address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        self.assertTrue(self.address_gml.isValid(), "Loading address")
        self.tn_gml = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        self.assertTrue(self.tn_gml.isValid(), "Loading thoroughfarename")
        self.pd_gml = QgsVectorLayer('test/address.gml|layername=postaldescriptor', 'pd', 'ogr')
        self.assertTrue(self.pd_gml.isValid(), "Loading address")
        self.au_gml = QgsVectorLayer('test/address.gml|layername=adminUnitname', 'au', 'ogr')
        self.assertTrue(self.au_gml.isValid(), "Loading address")
        fn = 'test_layer.shp'
        AddressLayer.create_shp(fn, self.address_gml.crs())
        self.layer = AddressLayer(fn, 'address', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.dataProvider().addAttributes([QgsField('TN_text', QVariant.String, len=254)])
        self.layer.updateFields()

    def tearDown(self):
        QgsVectorFileWriter.deleteShapeFile('test_layer.shp')

    def test_append(self):
        self.layer.append(self.address_gml)
        feat = self.layer.getFeatures().next()
        attrs = ['localId', 'PD_id', 'TN_id', 'AU_id']
        values = ['38.012.1.12.0295603CS6109N', 'ES.SDGC.PD.38.012.38570',
                  'ES.SDGC.TN.38.012.1', 'ES.SDGC.AU.38.012']
        for (attr, value) in zip(attrs, values):
            self.assertEquals(feat[attr], value)

    def test_join_field(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        feat = self.layer.getFeatures().next()
        attrs = ['TN_text', 'AU_text', 'postCode']
        values = ['MC ABASTOS (RESTO)', 'FASNIA', 38570]
        for (attr, value) in zip(attrs, values):
            self.assertEquals(feat[attr], value)

    def test_join_field_size(self):
        layer = PolygonLayer('Point', 'test', 'memory')
        layer.dataProvider().addAttributes([QgsField('A', QVariant.String, len=255)])
        layer.updateFields()
        self.layer.append(self.address_gml)
        self.layer.join_field(layer, 'TN_id', 'gml_id', ['A'], 'TN_')
        self.assertEquals(self.layer.pendingFields().field('TN_A').length(), 254)

    def test_join_void(self):
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.assertEquals(self.layer.featureCount(), 0)

    def test_to_osm(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        self.layer.source_date = 'foobar'
        data = osm.Osm(upload='ifyoudare')
        data.Node(0,0)
        data = self.layer.to_osm(data=data)
        self.assertEquals(data.upload, 'ifyoudare')
        self.assertEquals(data.tags['source:date'], 'foobar')
        self.assertEquals(len(data.elements), self.layer.featureCount() + 1)
        address = {n.tags['ref']: n.tags['addr:street']+n.tags['addr:housenumber'] \
            for n in data.nodes if 'ref' in n.tags}
        for feat in self.layer.getFeatures():
            t = address[feat['localId'].split('.')[-1]]
            self.assertEquals(feat['TN_text']+feat['designator'], t)

    def test_conflate(self):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        current_address = ["CJ CALLEJON (FASNIA)12", "CJ CALLEJON (FASNIA)13"]
        self.assertEquals(self.layer.featureCount(), 14)
        self.layer.conflate(current_address)
        self.assertEquals(self.layer.featureCount(), 10)
        self.layer.conflate(current_address)
        self.assertEquals(self.layer.featureCount(), 10)

    def test_del_address(self):
        self.layer.append(self.address_gml)
        building_osm = osm.Osm()
        building_osm.Node(0,0, dict(ref='8345806CS5284S'))
        building_osm.Node(0,0, dict(ref='8643403CS5284S'))
        building_osm.Node(0,0, dict(ref='8745401CS5284N'))
        building_osm.Node(0,0, dict(ref='8842304CS5284S'))
        building_osm.Node(0,0, dict(ref='8842306CS5284S'))
        building_osm.Node(0,0, dict(ref='8643407CS5284S'))
        self.assertEquals(self.layer.featureCount(), 14)
        self.layer.del_address(building_osm)
        self.assertEquals(self.layer.featureCount(), 6)
        self.layer.del_address(building_osm)
        self.assertEquals(self.layer.featureCount(), 6)

    def test_get_highway_names(self):
        layer = AddressLayer('test/address.geojson', 'address', 'ogr')
        highway = HighwayLayer('test/highway.geojson', 'highway', 'ogr')
        highway_names = layer.get_highway_names(highway)
        test = {
            'AV PAZ (FASNIA)': 'Avenida la Paz',
            'CL SAN JOAQUIN (FASNIA)': u'Calle San Joaquín',
            'CL HOYO (FASNIA)': 'Calle el Hoyo',
            'CJ CALLEJON (FASNIA)': u'Calleja/Callejón Callejon (Fasnia)'
        }
        for (k, v) in highway_names.items():
            self.assertEquals(v, test[k])


class TestHighwayLayer(unittest.TestCase):

    def test_init(self):
        layer = HighwayLayer()
        self.assertTrue(layer.isValid())
        self.assertEquals(layer.pendingFields()[0].name(), 'name')
        self.assertEquals(layer.crs().authid(), 'EPSG:4326')

    def test_read_from_osm(self):
        layer = HighwayLayer()
        data = osm.Osm()
        w1 = data.Way(((10,10), (15,15)), {'name': 'FooBar'})
        w2 = data.Way(((20,20), (30,30)))
        r = data.Relation([w2], {'name': 'BarTaz'})
        layer.read_from_osm(data)
        self.assertEquals(layer.featureCount(), 2)
        names = [feat['name'] for feat in layer.getFeatures()]
        self.assertIn('BarTaz', names)
        self.assertIn('FooBar', names)
        for f in layer.getFeatures():
            if f['name'] == 'FooBar':
                self.assertEquals(f.geometry().asPolyline(), [QgsPoint(10, 10), QgsPoint(15, 15)])
            if f['name'] == 'BarTaz':
                self.assertEquals(f.geometry().asPolyline(), [QgsPoint(20, 20), QgsPoint(30, 30)])

class TestDebugWriter(unittest.TestCase):

    def test_init(self):
        writer = DebugWriter('test', QgsCoordinateReferenceSystem(4326), 'memory')
        self.assertEquals(writer.fields[0].name(), 'note')
        self.assertEquals(writer.hasError(), 0)

    def test_add_point(self):
        writer = DebugWriter('test', QgsCoordinateReferenceSystem(4326), 'memory')
        writer.add_point(QgsPoint(0, 0), 'foobar')
        writer.add_point(QgsPoint(0, 0))

