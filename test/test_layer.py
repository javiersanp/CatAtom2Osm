# -*- coding: utf-8 -*-
import unittest
import mock
import random
import logging
logging.disable(logging.WARNING)

import gdal
from qgis.core import *
from PyQt4.QtCore import QVariant

import setup
from layer import *
from unittest_main import QgsSingleton

import gettext
if setup.platform.startswith('win'):
    if os.getenv('LANG') is None:
        os.environ['LANG'] = setup.language
gettext.install(setup.app_name.lower(), localedir=setup.localedir)

qgs = QgsSingleton() #QgsApplication([], False)


class TestPoint(unittest.TestCase):

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
        self.layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(self.layer.isValid())
        self.writer = self.layer.dataProvider()
        fields1 = []
        fields1.append(QgsField("A", QVariant.String))
        fields1.append(QgsField("B", QVariant.Int))
        self.writer.addAttributes(fields1)
        self.layer.updateFields()

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
        declined_filter = lambda feat: feat['conditionOfConstruction'] == 'declined'
        layer.append(self.fixture, query=declined_filter)
        self.assertTrue(layer.featureCount(), 2)
    
    def test_translate_field(self):
        ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.layer.startEditing()
        translations = {}
        for i in range(30):
            feat = QgsFeature(self.layer.pendingFields())
            value = ''.join([random.choice(ascii_uppercase) for j in range(10)])
            translations[value] = value.lower()
            feat['A'] = value
            self.layer.addFeature(feat)
        feat = QgsFeature(self.layer.pendingFields())
        feat['A'] = 'FooBar'
        self.layer.addFeature(feat)
        self.layer.commitChanges()
        self.assertGreater(self.layer.featureCount(), 0)
        self.layer.translate_field('TAZ', {})
        self.layer.translate_field('A', translations)
        for feat in self.layer.getFeatures():
            self.assertNotEquals(feat['A'], 'FooBar')
            self.assertEquals(feat['A'], feat['A'].lower())
        self.layer.translate_field('A', translations, clean=False)
        self.assertGreater(self.layer.featureCount(), 0)

    def test_reproject(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        features_before = layer.featureCount()
        feature_in = layer.getFeatures().next()
        crs_before = layer.crs()
        layer.reproject()
        feature_out = layer.getFeatures().next()
        self.assertEquals(layer.featureCount(), features_before)
        self.assertNotEquals(layer.crs(), crs_before)
        self.assertNotEquals(feature_in.geometry(), feature_out.geometry())
        self.assertEquals(feature_in.attributes(), feature_out.attributes())
    
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
        self.layer = PolygonLayer('Polygon', 'cadastralparcel', 'memory')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        self.layer.append(self.fixture, rename='')
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        self.writer = self.layer.dataProvider()

    def test_explode_multi_parts(self):
        mp = [f for f in self.layer.getFeatures() 
            if f.geometry().isMultipart()]
        self.assertGreater(len(mp), 0, "There are multipart features")
        nparts = sum([len(f.geometry().asMultiPolygon()) for f in mp])
        self.assertGreater(nparts, len(mp), "With more than one part")
        features_before = self.layer.featureCount()
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
            for ring in feature.geometry().asPolygon():
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
        self.layer.startEditing()
        self.writer.changeGeometryValues({feat1.id(): new_geom1})
        self.writer.changeGeometryValues({feat2.id(): new_geom2})
        self.layer.commitChanges()
        self.layer.clean_duplicated_nodes_in_polygons()
        features = self.layer.getFeatures()
        new_feat = features.next()
        clean_geom = new_feat.geometry()
        self.assertTrue(geom1.equals(clean_geom))
        new_feat = features.next()
        self.assertNotEquals(new_feat.id(), feat2.id())


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
        self.layer = ZoningLayer()
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.fixture = QgsVectorLayer('test/zoning.gml', 'zoning', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        self.layer.append(self.fixture)
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        self.writer = self.layer.dataProvider()
        self.layer.explode_multi_parts()

    def test_get_adjacents_and_features(self):
        (groups, features) = self.layer.get_adjacents_and_features()
        self.assertTrue(all([len(g) > 1 for g in groups]))
        for group in groups:
            for other in groups:
                if group != other:
                    self.assertTrue(all(p not in other for p in group))

    def test_clasify_zoning(self):
        (urban_zoning, rustic_zoning) = ZoningLayer.clasify_zoning(self.fixture)
        tc = urban_zoning.featureCount() + rustic_zoning.featureCount()
        self.assertGreaterEqual(self.fixture.featureCount(), tc)
        self.assertTrue(all([f['levelName'][3] == 'P' 
            for f in rustic_zoning.getFeatures()]))
        self.assertTrue(all([f['levelName'][3] == 'M' 
            for f in urban_zoning.getFeatures()]))
        
        
    def test_merge_adjacents(self):
        self.layer.merge_adjacents()
        (groups, features) = self.layer.get_adjacents_and_features()
        self.assertEquals(len(groups), 0)
        #self.layer.setCrs(QgsCoordinateReferenceSystem(32628))
        #self.layer.reproject()
        #self.layer.export('zoning.geojson', 'GeoJSON')

    def test_set_labels(self):
        self.layer.set_labels('%05d')
        i = 1
        for feat in self.layer.getFeatures():
            self.assertEquals(feat['label'], '%05d' % i)
            i += 1


class TestConsLayer(unittest.TestCase):

    def setUp(self):
        self.layer = ConsLayer()
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        self.layer.append(self.fixture, rename='')
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        self.writer = self.layer.dataProvider()

    def test_is_building(self):
        self.assertTrue(ConsLayer.is_building({'localId': 'foobar'}))
        self.assertFalse(ConsLayer.is_building({'localId': 'foo_bar'}))
    
    def test_is_part(self):
        self.assertTrue(ConsLayer.is_part({'localId': 'foo_part1'}))
        self.assertFalse(ConsLayer.is_part({'localId': 'foo_PI.1'}))

    def test_is_pool(self):
        self.assertTrue(ConsLayer.is_pool({'localId': 'foo_PI.1'}))
        self.assertFalse(ConsLayer.is_pool({'localId': 'foo_part1'}))

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

    def test_remove_parts_below_ground(self):
        to_clean = [f.id() for f in self.layer.search('lev_above=0')]
        self.assertGreater(len(to_clean), 0, 'There are parts below ground')
        self.layer.remove_parts_below_ground()
        to_clean = [f.id() for f in self.layer.search('lev_above=0')]
        self.assertEquals(len(to_clean), 0, 'There are not parts below ground')

    def test_merge_greatest_part(self):
        refs = {'9042901CS5294S': 2, # 2 parts inside with a hole, 1 outside
                '8646414CS5284N': 0, '8442825CS5284S': 0,  # single part 
                '8544910CS5284S': 1, # 2 parts inside
                '8544911CS5284S': 3, # 4 parts inside
                '8645910CS5284N': 2, # 3 parts, one inside
                '8342404CS5284S': 0, # 4 parts inside in the same floor
        }
        self.layer.explode_multi_parts()
        for ref in refs.keys():
            building = self.layer.search("localId = '%s'" % ref).next()
            self.assertEquals(building['localId'], ref, "Find building")
            parts = [f for f in self.layer.search("localId LIKE '%%%s_part%%'" % ref)]
            self.assertTrue(self.layer.startEditing())
            to_clean, to_change = self.layer.merge_greatest_part(building, parts)
            self.writer.deleteFeatures(to_clean)
            self.writer.changeAttributeValues(to_change)
            oparts = [f for f in self.layer.search("localId LIKE '%%%s_part%%'" % ref)]
            self.assertTrue(self.layer.commitChanges())
            self.assertEquals(refs[ref], len(oparts), "Number of parts %s "
                "%d != %d" % (ref, refs[ref], len(oparts)))
            self.assertGreater(building['lev_above'], 0, "Copy levels")

    def test_index_of_building_and_parts(self):
        (buildings, parts) = self.layer.index_of_building_and_parts()
        self.assertGreaterEqual(len(buildings), 0)
        self.assertGreater(len(parts), 0)
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

    def test_merge_building_parts(self):
        self.layer.explode_multi_parts()
        self.layer.remove_parts_below_ground()
        (buildings, parts) = self.layer.index_of_building_and_parts()
        self.layer.merge_building_parts()
        for (ref, group) in buildings.items():
            if ref in parts:
                for building in group:
                    building_area = round(building.geometry().area()*100)
                    parts_area = round(sum([part.geometry().area() 
                        for part in parts[ref]])*100)
                    if building_area == parts_area:
                        request = QgsFeatureRequest()
                        request.setFilterFids([building.id()])
                        feat = self.layer.getFeatures(request).next()
                        self.assertTrue(feat['lev_above'])

    def test_add_topological_points(self):
        refs = [
            ('8842708CS5284S', QgsPoint(358821.08, 3124205.68)),
            ('8842708CS5284S_part1', QgsPoint(358821.08, 3124205.68)),
            ('8942325CS5284S', QgsPoint(358789.2925, 3124247.643)),
            ('8942325CS5284S_part1', QgsPoint(358789.2925, 3124247.643))
        ]
        self.layer.explode_multi_parts()
        for ref in refs:
            building = self.layer.search("localId = '%s'" % ref[0]).next()
            self.assertNotIn(ref[1], building.geometry().asPolygon()[0])
        self.layer.add_topological_points()
        for ref in refs:
            building = self.layer.search("localId = '%s'" % ref[0]).next()
            self.assertIn(ref[1], building.geometry().asPolygon()[0])

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

    def test_set_tasks(self):
        zoning = QgsVectorLayer('test/zoning.gml', 'zoning', 'ogr')
        (urban_zoning, rustic_zoning) = ZoningLayer.clasify_zoning(zoning)
        urban_zoning.explode_multi_parts()
        urban_zoning.merge_adjacents()
        rustic_zoning.explode_multi_parts()
        self.layer.set_tasks(urban_zoning, rustic_zoning)
        self.assertTrue(all([f['task'] != 'NULL' for f in self.layer.getFeatures()]))

    def test_remove_duplicated_holes_parts(self):
        exp = QgsExpression('localId ILIKE \'%_part%\'')
        request = QgsFeatureRequest(exp)
        for feat in self.layer.getFeatures(request):
            hole = len(feat.geometry().asPolygon()) > 1
            if hole: break
        self.assertTrue(hole)
        self.layer.remove_duplicated_holes()
        for feat in self.layer.getFeatures(request):
            hole = len(feat.geometry().asPolygon()) > 1
            if hole: break
        self.assertFalse(hole)

    def test_remove_duplicated_holes_buildings(self):
        refs = ['8642309CS5284S', '8646411CS5284N', '8841602CS5284S']
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = self.layer.getFeatures(request).next()
            geom = feat.geometry().asPolygon()
            self.assertGreater(len(geom), 1)
        self.layer.remove_duplicated_holes()
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = self.layer.getFeatures(request).next()
            geom = feat.geometry().asPolygon()
            self.assertEquals(len(geom), 1)

    def test_move_address(self):
        refs = {
            '38.012.10.10.8643403CS5284S': 'Entrance',
            '38.012.10.11.8842304CS5284S': 'Entrance',
            '38.012.10.13.8842305CS5284S': 'relation',
            '38.012.10.14.8643404CS5284S': 'corner',
            '38.012.10.14.8643406CS5284S': 'Parcel',
            '38.012.10.2.8642321CS5284S': 'Entrance',
            '38.012.15.73.8544911CS5284S': 'remote'
        }
        address = AddressLayer()
        address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        address.append(address_gml)
        self.layer.explode_multi_parts()
        self.layer.move_address(address)
        self.assertEquals(address.featureCount(), 7)
        for ad in address.getFeatures():
            self.assertEquals(ad['spec'], refs[ad['localId']])
            if ad['spec'] == 'Entrance':
                refcat = ad['localId'].split('.')[-1]
                building = self.layer.search("localId = '%s'" % refcat).next()
                self.assertTrue(ad.geometry().touches(building.geometry()))

    @mock.patch('layer.log')
    def test_check_levels_and_area(self, mock_lock):
        refs = ['7239208CS5273N', '38012A00400007']
        self.layer.check_levels_and_area()
        self.assertEquals(mock_lock.info.mock_calls[0][1][1], '1: 465, 2: 244, 3: 97, 4: 18, 5: 1')
        self.assertEquals(mock_lock.info.mock_calls[1][1][1], '1: 153, 2: 7')
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = self.layer.getFeatures(request).next()
            self.assertNotEquals(feat['fixme'], '')


class TestAddressLayer(unittest.TestCase):

    def setUp(self):
        self.layer = AddressLayer()
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        self.assertTrue(self.address_gml.isValid(), "Loading address")
        self.tn_gml = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        self.assertTrue(self.tn_gml.isValid(), "Loading thoroughfarename")
        self.pd_gml = QgsVectorLayer('test/address.gml|layername=postaldescriptor', 'pd', 'ogr')
        self.assertTrue(self.pd_gml.isValid(), "Loading address")
        self.au_gml = QgsVectorLayer('test/address.gml|layername=adminUnitname', 'au', 'ogr')
        self.assertTrue(self.au_gml.isValid(), "Loading address")
        
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


class TestDebugWriter(unittest.TestCase):

    def test_init(self):
        writer = DebugWriter('test', QgsCoordinateReferenceSystem(4326), 'memory')
        self.assertEquals(writer.fields[0].name(), 'note')
        self.assertEquals(writer.hasError(), 0)
        
    def test_add_point(self):
        writer = DebugWriter('test', QgsCoordinateReferenceSystem(4326), 'memory')
        writer.add_point(QgsPoint(0, 0), 'foobar')
        writer.add_point(QgsPoint(0, 0))

