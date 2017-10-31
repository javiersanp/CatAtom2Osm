# -*- coding: utf-8 -*-
"""Statistics report"""

from collections import OrderedDict

import setup

class Report(object):

    def __init__(self):
        self.values = {}
        self.titles = {
            'mun_name': _('Municipality: {}'),
            'mun_code': _(u'Code: {}'),
            'mun_area': _(u'Area: {} km²'),
            'input': _('=Input data='),
            'inp_address': _('Addresses: {}'),
            'inp_address_entrance': _('  Type entrance: {}'),
            'inp_address_parcel': _('  Type parcel: {}'),
            'inp_zip_codes': _('Postal codes: {}'),
            'inp_street_names': _('Street names: {}'),
            'inp_buildings': _('Buildings: {}'),
            'inp_parts': _('Parts of buildings: {}'),
            'inp_pools': _('Swimming pools: {}'),
            'process': _('=Process='),
            'addresses_without_number': _('Addresses without house number deleted: {}'),
            'orphand_addresses': _('Addresses without associated building deleted: {}'),
            'multiple_addresses': _('Addresses belonging to multiple buildings deleted: {}'),
            'output': _('=Output data='),
            'out_address': _('Addresses: {}'),
            'out_address_entrance': _('  In entrance nodes: {}'),
            'out_address_building': _('  In buildings: {}'),
            'vertex_close_building': _('Close vertices merged: {}'),
            'vertex_topo_building': _('Topological points created: {}'),
            'geom_rings_building': _('Invalid geometry rings deleted: {}'),
            'geom_invalid_building': _('Invalid geometries deleted: {}'),
            'orphand_parts_building': _("Parts outside footprint deleted: {}"), 
            'below_removed_building': _("Parts with no floors above ground: {}"),
        }
        self.groups = OrderedDict([
            ('head', ['mun_name', 'mun_code', 'mun_area']),
            ('input', ['inp_address', 'inp_address_entrance', 'inp_address_parcel', 
                'inp_zip_codes', 'inp_street_names',
                'inp_buildings', 'inp_parts', 'inp_pools']),
            ('process', ['addresses_without_number','orphand_addresses', 
                'multiple_addresses', 
                'orphand_parts_building', 'below_removed_building',
                'vertex_close_building', 'vertex_topo_building', 
                'geom_rings_building', 'geom_invalid_building']),
            ('output', ['out_address', 'out_address_entrance', 'out_address_building'])
        ])

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
                output += setup.eol + self.titles[group_key] + setup.eol
            for mem_key in members:
                if mem_key in self.values:
                    output += self.titles[mem_key].format(self.values[mem_key]) + setup.eol
        return output

instance = Report()

"""
=Procesado=
 Direcciones sin número de portal eliminadas:
 Direcciones correspondientes a varios edificio eliminadas:
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
Direcciones en OSM:
Direcciones rechazadas por existir en OSM:
Edificios/piscinas en OSM:
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

