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
    tags['addr:postcode'] = str(feature['postCode'])
    tags['addr:city'] = feature['AU_text']
    if feature['spec'] == 'Entrance':
        tags['entrance'] = 'yes'
    return tags
    
def building_tags(feature):
    """Translations for constructions layer"""
    translations = {
        'condition': {
        	'ruin': '{"ruins": "yes"}',
        	'declined': '{"disused": "yes"}',
        },
        'currentUse': {
            '1_residential': '{"building": "residential"}',
            '2_agriculture': '{"building": "barn"}',
            '3_industrial': '{"building": "industrial"}',
            '4_1_office': '{"building": "office"}',
            '4_2_retail': '{"building": "retail"}',
            '4_3_publicServices': '{"building": "public"}'
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
    if '_part' in feature['localId']:
        tags['building:part'] = 'yes'
    if feature['lev_above']:
        tags['building:levels'] = str(feature['lev_above'])
    if feature['lev_below']:
        tags['building:levels:underground'] = str(feature['lev_below'])
    return tags

