import unittest
import mock
import random

from translate import *


class TestTranslate(unittest.TestCase):

    def test_all_tags(self):
        tags = {'a': 1, 'b': 2, 'c': 3}
        fields = []
        for k in tags.keys():
            f = mock.MagicMock()
            f.name.return_value = k
            fields.append(f)
        feat = mock.MagicMock()
        feat.fields.return_value = fields
        feat.side_effect = tags.values()
        dest = all_tags(feat)
        for (k, v) in tags.items():
            self.assertTrue(dest[k], str(v))

    def test_address_tags(self):
        feat = {
            'TN_text': '111', 
            'designator': '222',
            'postCode': '',
            'spec': 'Parcel'
        }
        tags = address_tags(feat)
        self.assertEquals(tags['addr:street'], '111')
        self.assertEquals(tags['addr:housenumber'], '222')
        self.assertNotIn('addr:postcode', tags)
        self.assertNotIn('entrance', tags)
        feat['spec'] = 'Entrance'
        feat['postCode'] = '333'
        tags = address_tags(feat)
        self.assertEquals(tags['entrance'], 'yes')
        self.assertEquals(tags['addr:postcode'], '00333')

    def test_building_tags(self):
        building_values = ('residential', 'barn', 'industrial', 'office', 
            'retail', 'public')
        use_values = ('1_residential', '2_agriculture', '3_industrial', 
            '4_1_office', '4_2_retail', '4_3_publicServices')
        feat = {
            'condition': 'functional',
            'currentUse': 'foobar',
            'nature': None,
            'localId': 'foobar',
            'lev_above': 0,
            'lev_below': 0
        }
        tags = building_tags(feat)
        self.assertNotIn('abandoned:building', tags)
        self.assertNotIn('disused:building', tags)
        self.assertEquals(tags['building'], 'yes')
        self.assertNotIn('building:levels', tags)
        self.assertNotIn('building:levels:underground', tags)
        use = random.randint(0, len(use_values)-1)
        feat['currentUse'] = None
        feat['condition'] = 'ruin'
        feat['nature'] = 'openAirPool'
        feat['lev_above'] = 1
        feat['lev_below'] = 2
        feat['localId'] = 'foobar_part1'
        tags = building_tags(feat)
        self.assertEquals(tags['building'], 'ruins')
        self.assertEquals(tags['abandoned:building'], 'yes')
        self.assertEquals(tags['leisure'], 'swimming_pool')
        self.assertEquals(tags['building:part'], 'yes')
        self.assertEquals(tags['building:levels'], '1')
        self.assertEquals(tags['building:levels:underground'], '2')
        use = random.randint(0, len(use_values)-1)
        feat['currentUse'] = use_values[use]
        feat['condition'] = 'declined'
        tags = building_tags(feat)
        self.assertEquals(tags['building'], 'yes')
        self.assertEquals(tags['disused:building'], building_values[use])
        use = random.randint(0, len(use_values)-1)
