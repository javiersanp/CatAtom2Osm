# -*- coding: utf-8 -*-
"""
Parsing of highway names
"""

import os
import re

import setup

try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
except:
    fuzz = None

MATCH_THR = 60


def normalize(text):
    return re.sub(' *\(.*\)', '', text.lower().strip())

def parse(name):
    """Transform the name of a street from Cadastre conventions to OSM ones."""
    name = re.sub('[,]+', ', ', name).strip() # Avoids comma without trailing space
    result = []
    for (i, word) in enumerate(re.split('[ ]+', name.strip())):
        nude_word = re.sub('^\(|\)$', '', word) # Remove enclosing parenthesis
        if i == 0:
            try:
                new_word = setup.highway_types[word]
            except KeyError:
                new_word = word
        elif nude_word in setup.lowcase_words: # Articles
            new_word = word.lower()
        elif "'" in word[1:-1]: # Articles with aphostrope
            left = word.split("'")[0]
            right = word.split("'")[-1]
            if left in ['C', 'D', 'L', 'N', 'S']:
                new_word = left.lower() + "'" + right.title()
            elif right in ['S', 'N', 'L', 'LA', 'LS']:
                new_word = left.title() + "'" + right.lower()
            else:
                new_word = word.title()
        else:
            new_word = word.title()
        new_word = new_word.replace(u'·L', u'·l') # Letra ele geminada
        new_word = new_word.replace(u'.L', u'·l') # Letra ele geminada
        result.append(new_word)
    return ' '.join(result).strip()

def match(name, choices):
    """
    Fuzzy search best match for string name in iterable choices, if the result
    is not good enough returns the name parsed
    
    Args:
        name (str): String to look for
        choices (list): Iterable with choices
    """
    if fuzz:
        normalized = [normalize(c) for c in choices]
        matching = process.extractOne(normalize(parse(name)), 
            normalized, scorer=fuzz.token_sort_ratio)
        if matching and matching[1] > MATCH_THR:
            return choices[normalized.index(matching[0])]
    return parse(name)

def dsmatch(name, dataset, fn):
    """
    Fuzzy search best matching object for string name in dataset
    
    Args:
        name (str): String to look for
        dataset (list): List of objects to search for
        fn (function): Function to obtain a string from a element of the dataset
        
    Returns:
        First element with the maximun fuzzy ratio.
    """
    max_ratio = 0
    matching = None
    for e in dataset:
        if fuzz:
            ratio = fuzz.token_set_ratio(normalize(name), normalize(fn(e)))
            if ratio > max_ratio:
                max_ratio = ratio
                matching = e
        elif normalize(name) == normalize(fn(e)):
            matching = e
            break
    return matching

