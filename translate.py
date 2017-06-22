# -*- coding: utf-8 -*-
"""Translations from source fields to OSM tags"""

import json

def all_tags(feature):
    """All fields to tags translations"""
    tags = {}
    for attr in [f.name() for f in feature.fields()]:
        tags[attr] = str(feature[attr])
    return tags
    
def address_tags(feature):
    """Translatios for address layer fields"""
    tags = {}
    tags['addr:street'] = feature['TN_text']
    tags['addr:housenumber'] = feature['designator']
    try:
        tags['addr:postcode'] = '%05d' % int(feature['postCode'])
    except:
        pass
    if feature['spec'] == 'Entrance':
        tags['entrance'] = 'yes'
    return tags
    
def building_tags(feature):
    """Translations for constructions layer"""
    building_key = {
        'functional': 'building',
        'declined': 'disused:building',
        'ruin': 'abandoned:building',
    }
    get_building_key = lambda feat: building_key.get(feat['condition'], 'building')
    translations = {
        'condition': {
        	'declined': '{"building": "yes"}',
        	'ruin': '{"building": "ruins"}',
        },
        'currentUse': {
            '1_residential': '{"%s": "residential"}' % get_building_key(feature),
            '2_agriculture': '{"%s": "barn"}' % get_building_key(feature),
            '3_industrial': '{"%s": "industrial"}' % get_building_key(feature),
            '4_1_office': '{"%s": "office"}' % get_building_key(feature),
            '4_2_retail': '{"%s": "retail"}' % get_building_key(feature),
            '4_3_publicServices': '{"%s": "public"}' % get_building_key(feature),
        },
        'nature': {
            'openAirPool': '{"leisure": "swimming_pool"}'
        }
    }
    tags = {}
    if '_' not in feature['localId']:
        tags['building'] = 'yes'
    for field, action in translations.items():
        for value, new_tags in action.items():
            if feature[field] == value:
                tags.update(json.loads(new_tags))
    if feature['condition'] == 'ruin' and feature['currentUse'] == None:
        tags['abandoned:building'] = 'yes'
    if '_part' in feature['localId']:
        tags['building:part'] = 'yes'
    if feature['lev_above']:
        tags['building:levels'] = str(feature['lev_above'])
    if feature['lev_below']:
        tags['building:levels:underground'] = str(feature['lev_below'])
    return tags

