# -*- coding: utf-8 -*-
"""
Parsing of highway names
"""

import os
import re
import logging

import setup
import csvtools

log = logging.getLogger(setup.app_name + "." + __name__)


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
                log.warning(_("The higway type '%s' is not known"), word)
        elif nude_word in setup.lowcase_words: # Articles
            new_word = word.lower()
        elif len(word) > 3 and word[1] == "'": # Articles with aphostrope
            new_word = word[0:2].lower() + word[2:].title()
        else:
            new_word = word.title()
        new_word = new_word.replace(u'·L', u'·l') # Letra ele geminada
        result.append(new_word)
    return ' '.join(result).strip()

def get_translations(names_layer, output_folder):
    """
    If there exists the configuration file 'highway_types.csv', read it, 
    else write one with default values. If don't exists the translations file 
    'highway_names.csv', creates one parsing names_layer, else reads and returns
    it as a dictionary.
    
    Args:
        names_layer (AddressLayer): Layer with street names (thoroughfarename)
        output_folder (str): Directory where the source files are located
    
    Returns:
        (dict, bool): Dictionary with highway names translations and a flag to
        alert if it's new (there wasen't a previous translations file)
    """
    highway_types_path = os.path.join(setup.app_path, 'highways_types.csv')
    if not os.path.exists(highway_types_path):
        csvtools.dict2csv(highway_types_path, setup.highway_types)
    else:
        csvtools.csv2dict(highway_types_path, setup.highway_types)
    highway_names_path = os.path.join(output_folder, 'highway_names.csv')
    if not os.path.exists(highway_names_path):
        highway_names = {}
        for feat in names_layer.getFeatures():
            name = feat['text']
            highway_names[name] = parse(name)
            csvtools.dict2csv(highway_names_path, highway_names)
        log.info(_("The translation file '%s' have been writen in '%s'"),
            'highway_names.csv', output_folder)
        log.info(_("Please, check it before continue"))
        return (highway_names, True)
    else:
        return (csvtools.csv2dict(highway_names_path, {}), False)

