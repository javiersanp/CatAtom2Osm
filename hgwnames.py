# -*- coding: utf-8 -*-
"""
Parsing of highway names
"""

import os
import re

import setup
import csvtools


def parse(name):
    """Transform the name of a street from Cadastre conventions to OSM ones."""
    name = re.sub('[,]+', ', ', name).strip() # Avoids comma without trailing space
    result = []
    for (i, word) in enumerate(re.split('[ ]+', name)):
        nude_word = re.sub('^\(|\)$', '', word) # Remove enclosing parenthesis
        if i == 0:
            try:
                new_word = setup.highway_types[word]
            except KeyError:
                new_word = word
        elif nude_word in setup.lowcase_words: # Articles
            new_word = word.lower()
        elif len(word) > 3 and word[1] == "'": # Articles with aphostrope
            new_word = word[0:2].lower() + word[2:].title()
        else:
            new_word = word.title()
        new_word = new_word.replace(u'·L', u'·l') # Letra ele geminada
        result.append(new_word)
    return ' '.join(result).strip()

def get_translations(address_layer, output_folder, street_fn, housenumber_fn):
    """
    If there exists the configuration file 'highway_types.csv', read it, 
    else write one with default values. If don't exists the translations file 
    'highway_names.csv', creates one parsing names_layer, else reads and returns
    it as a dictionary.
    
    * 'highway_types.csv' is located in the application path and contains 
    translations from abreviaturs to full types of highways.
    * 'highway_names.csv' is located in the outputh folder and contains 
    corrections for original highway names.
    
    Args:
        address_layer (AddressLayer): Layer with addresses
        output_folder (str): Directory where the source files are located
        street_fn (str): Name of the field for the address street name
        housenumber_fn (str): Name of the field for the address housenumber
    
    Returns:
        (dict, bool): Dictionary with highway names translations and a flag to
        alert if it's new (there wasen't a previous translations file)
    """
    highway_types_path = os.path.join(setup.app_path, 'highway_types.csv')
    if not os.path.exists(highway_types_path):
        csvtools.dict2csv(highway_types_path, setup.highway_types)
    else:
        csvtools.csv2dict(highway_types_path, setup.highway_types)
    highway_names_path = os.path.join(output_folder, 'highway_names.csv')
    if not os.path.exists(highway_names_path):
        highway_names = {}
        for feat in address_layer.getFeatures():
            name = feat[street_fn]
            if not name in highway_names:
            	highway_names[name] = ''
            if highway_names[name] == '' and \
            	not re.match(setup.no_number, feat[housenumber_fn]):
		            highway_names[name] = parse(name)
            csvtools.dict2csv(highway_names_path, highway_names)
        return (highway_names, True)
    else:
        return (csvtools.csv2dict(highway_names_path, {}), False)

