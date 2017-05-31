import unittest
import mock
import random

import gdal
from qgis.core import *
from PyQt4.QtCore import QVariant

import setup
from layer import *

QgsApplication.setPrefixPath(setup.qgs_prefix_path, True)
qgs = QgsApplication([], False)

def setUpModule():
    qgs.initQgis()
    gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
    gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')

def tearDownModule():
    qgs.exitQgis()
    gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'NO')
    gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')


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
            QgsPoint(0, 0)
        ]])
        angle_thr = 5
        cath_thr = 0.5
        (test, a, c) = Point(50, 0.4).is_corner_with_context(square, angle_thr, cath_thr)
        self.assertTrue(test)
        (test, a, c) = Point(105, 51).is_corner_with_context(square, angle_thr, cath_thr)
        self.assertTrue(test)
        (test, a, c) = Point(5.1, 100).is_corner_with_context(square, angle_thr, cath_thr)
        self.assertTrue(test)
        (test, a, c) = Point(0.4, 50).is_corner_with_context(square, angle_thr, cath_thr)
        self.assertFalse(test)
    
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


class TestConsLayer(unittest.TestCase):

    def setUp(self):
        self.layer = ConsLayer()
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        self.layer.append(self.fixture, rename={})
        self.assertEquals(self.layer.featureCount(), self.fixture.featureCount())
        self.writer = self.layer.dataProvider()

    def test_is_building(self):
        self.assertTrue(ConsLayer.is_building('foobar'))
        self.assertFalse(ConsLayer.is_building('foo_bar'))
    
    def test_is_part(self):
        self.assertTrue(ConsLayer.is_part('foo_part1'))
        self.assertFalse(ConsLayer.is_part('foo_P1.1'))

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
        exp = QgsExpression("lev_above=0")
        request = QgsFeatureRequest(exp)
        to_clean = [f.id() for f in self.layer.getFeatures(request)]
        self.assertGreater(len(to_clean), 0, 'There are parts below ground')
        self.layer.remove_parts_below_ground()
        request = QgsFeatureRequest(exp)
        to_clean = [f.id() for f in self.layer.getFeatures(request)]
        self.assertEquals(len(to_clean), 0, 'There are not parts below ground')

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
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            building = self.layer.getFeatures(request).next()
            self.assertEquals(building['localId'], ref, "Find building")
            exp = QgsExpression("localId LIKE '%%%s_part%%'" % ref)
            request = QgsFeatureRequest(exp)
            parts = [f for f in self.layer.getFeatures(request)]
            self.assertTrue(self.layer.startEditing())
            self.layer.merge_greatest_part(building, parts)
            oparts = [f for f in self.layer.getFeatures(request)]
            self.assertTrue(self.layer.commitChanges())
            m = "Number of parts"
            self.assertEquals(refs[building['localId']], len(oparts), m)
            self.assertGreater(building['lev_above'], 0, "Copy levels")

    def test_index_of_building_and_parts(self):
        (features, buildings, parts) = self.layer.index_of_building_and_parts()
        self.assertEquals(len(features), self.layer.featureCount())
        self.assertTrue(all([features[fid].id() == fid for fid in features]))
        self.assertGreater(len(buildings), 0)
        self.assertGreater(len(parts), 0)
        self.assertTrue(all([localid==features[fid]['localid'] 
            for (localid, fids) in buildings.items() for fid in fids]))
        self.assertTrue(all([localid==features[fid]['localid'][0:14] 
            for (localid, fids) in parts.items() for fid in fids]))
                
    def test_merge_building_parts(self):
        self.layer.explode_multi_parts()
        self.layer.remove_parts_below_ground()
        (features, buildings, building_parts) = self.layer.index_of_building_and_parts()
        self.layer.merge_building_parts()
        for (localId, fids) in buildings.items():
            if localId in building_parts:
                for fid in fids:
                    building = features[fid]
                    parts_in_building = [features[i] for i in building_parts[localId]]
                    building_area = round(building.geometry().area()*100)
                    parts_area = round(sum([part.geometry().area() 
                        for part in parts_in_building])*100)
                    if building_area == parts_area:
                        request = QgsFeatureRequest()
                        request.setFilterFids([fid])
                        feat = self.layer.getFeatures(request).next()
                        self.assertTrue(feat['lev_above'])

    def test_create_dict_of_vertex_and_features(self):
        (vertexs, features) = self.layer.create_dict_of_vertex_and_features()
        self.assertEquals(len(features), self.layer.featureCount())
        self.assertTrue(all([features[fid].id() == fid for fid in features]))
        self.assertGreater(len(vertexs), 0)
        self.assertTrue(all([QgsGeometry().fromPoint(vertex) \
            .intersects(features[fid].geometry()) 
                for (vertex, fids) in vertexs.items() for fid in fids]))

    def test_get_vertexs(self):
        vertexs = self.layer.get_vertexs()
        vcount = 0
        for feature in self.layer.getFeatures(): 
            for ring in feature.geometry().asPolygon():
                for point in ring[0:-1]:
                    vcount += 1
        self.assertEquals(vcount, vertexs.featureCount())
        
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
        feat = self.layer.getFeatures().next()
        geom = feat.geometry()
        new_geom = QgsGeometry(geom)
        l = len(new_geom.asPolygon()[0])
        self.assertGreater(l, 3)
        v = new_geom.vertexAt(l-1)
        self.assertTrue(new_geom.insertVertex(v.x(), v.y(), l-1))
        v = new_geom.vertexAt(0)
        self.assertTrue(new_geom.insertVertex(v.x(), v.y(), 0))
        v = new_geom.vertexAt(l/2)
        self.assertTrue(new_geom.insertVertex(v.x(), v.y(), l/2))
        self.assertTrue(new_geom.insertVertex(v.x(), v.y(), l/2))
        self.layer.startEditing()
        self.writer.changeGeometryValues({feat.id(): new_geom})
        self.layer.commitChanges()
        self.layer.clean_duplicated_nodes_in_polygons()
        new_feat = self.layer.getFeatures().next()
        clean_geom = new_feat.geometry()
        self.assertEquals(geom.asPolygon(), clean_geom.asPolygon())
    

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
