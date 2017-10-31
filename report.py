# -*- coding: utf-8 -*-
"""Statistics report"""

from collections import OrderedDict

import setup

class Report(object):

    def __init__(self):
        self.values = {}
        self.titles = {
            'mun_name': 'Municipality: {}',
            'mun_code': u'Code: {}',
            'mun_area': u'Area: {} km²',
            'input': '=Input data=',
            'inp_address': 'Addresses: {}',
            'inp_address_entrance': '  Type entrance: {}',
            'inp_address_parcel': '  Type parcel: {}',
            'inp_zip_codes': 'Postal codes: {}',
            'inp_street_names': 'Street names: {}',
            'inp_buildings': 'Buildings: {}',
            'inp_parts': 'Parts of buildings: {}',
            'inp_pools': 'Swimming pools: {}',
            'process': '=Process=',
            'addresses_without_number': 'Addresses without house number deleted: {}',
            'orphand_addresses': 'Addresses without associated building deleted: {}',
            'multiple_addresses': 'Addresses belonging to multiple buildings deleted: {}',
            'output': '=Output data=',
            'out_address': 'Addresses: {}',
            'out_address_entrance': '  In entrance nodes: {}',
            'out_address_building': '  In buildings: {}',
        }
        self.groups = OrderedDict([
            ('head', ['mun_name', 'mun_code', 'mun_area']),
            ('input', ['inp_address', 'inp_address_entrance', 'inp_address_parcel', 
                'inp_zip_codes', 'inp_street_names',
                'inp_buildings', 'inp_parts', 'inp_pools']),
            ('process', ['addresses_without_number','orphand_addresses', 
                'multiple_addresses']),
            ('output', ['out_address'])
        ])
        #Direcciones correspondientes a varios edificio eliminadas: !

    def __setattr__(self, key, value):
        if key in ['values', 'titles', 'groups']:
            super(Report, self).__setattr__(key, value)
        else:
            self.values[key] = value

    def __getattr__(self, key):
        if key in ['values', 'titles', 'groups']:
            return super(Report, self).__getattr__(key)
        else:
            return self.values[key]

    def to_string(self):
        output = ''
        for group_key, members in self.groups.items():
            is_void = all(k not in self.values for k in members)
            if group_key in self.titles and not is_void:
                output += setup.eol + _(self.titles[group_key]) + setup.eol
            for mem_key in members:
                if mem_key in self.values:
                    output += _(self.titles[mem_key]).format(self.values[mem_key]) + setup.eol
        return output

instance = Report()

"""
Municipio: 
Código: 
Superficie: 

=Datos de entrada=
Direcciones:
  Tipo entrada: 
  Tipo parcela:
Edificios:
Partes de edificios:
Piscinas:

=Procesado=
Direcciones sin número de portal eliminadas:
Direcciones correspondientes a varios edificio eliminadas: !
Partes de edificio fuera del contorno eliminadas:
Partes bajo rasante eliminadas: 
Contornos de edificio creados:
Edificios añadidos tras separar geometrías multiparte:
Anillos de geometrías no válidos eliminados:
Geometrías no válidas eliminadas:
Vértices próximos fusionados:
Puntos topológicos creados:
Vértices simplificados:
Partes de edificio fusionadas al contorno:
Partes adyacentes fusionadas:

Combinación:
Direcciones existentes en OSM:
Direcciones rechazadas por existir en OSM:
Edificios/piscinas existentes en OSM:
Edificios/piscinas con conflicto:

=Datos de salida=
Nodos:
Vías:
Relaciones:
Edificios:
Partes de edificios:
Piscinas:
Direcciones:
  Tipo entrada:
  En vía del edificio:
Tareas de rústica generadas:
Tareas de urbana generadas:
Histograma de tipos de edificación:
Histograma de distribución de plantas:

=Avisos=
Fixme
"""

