# -*- coding: utf-8 -*-
"""Statistics report"""

from collections import OrderedDict
from datetime import datetime
import codecs

import setup

class Report(object):

    def __init__(self):
        self.values = {'date': datetime.now().strftime('%x')}
        self.titles = {
            'mun_name': _('Municipality: {}'),
            'mun_code': _('Code: {}'),
            'mun_area': _(u'Area: {} km²'),
            'date': _('Date: {}'),
            'input': _('=Input data='),
            'inp_address': _('Addresses: {}'),
            'inp_address_entrance': _('  Type entrance: {}'),
            'inp_address_parcel': _('  Type parcel: {}'),
            'inp_zip_codes': _('Postal codes: {}'),
            'inp_street_names': _('Street names: {}'),
            'inp_buildings': _('Buildings: {}'),
            'inp_parts': _('Buildings parts: {}'),
            'inp_pools': _('Swimming pools: {}'),
            'building_date': _('Buildings source date: {}'),
            'address_date': _('Addresses source date: {}'),
            'process': _('=Process='),
            'addresses_without_number': _('Addresses without house number deleted: {}'),
            'orphand_addresses': _('Addresses without associated building deleted: {}'),
            'multiple_addresses': _('Addresses belonging to multiple buildings deleted: {}'),
            'output': _('=Output data='),
            'out_address': _('Addresses: {}'),
            'out_address_entrance': _('  In entrance nodes: {}'),
            'out_address_building': _('  In buildings: {}'),
            'out_addr_str': _('  Type addr:street: {}'),
            'out_addr_plc': _('  Type addr:place: {}'),
            'vertex_close_building': _('Close vertices merged: {}'),
            'vertex_topo_building': _('Topological points created: {}'),
            'vertex_simplify_building': _("Simplified vertices: {}"),
            'geom_rings_building': _('Invalid geometry rings deleted: {}'),
            'geom_invalid_building': _('Invalid geometries deleted: {}'),
            'orphand_parts': _("Parts outside footprint deleted: {}"), 
            'underground_parts': _("Parts with no floors above ground: {}"),
            'new_footprints': _("Building footprints created: {}"),
            'parts_to_footprint': _("Parts merged to the footprint: {}"),
            'adjacent_parts': _("Adjacent parts merged: {}"),
            'multipart_geoms_building': _("Buildings with multipart geometries: {}"),
            'exploded_parts_building': _("Buildings resulting from spliting multiparts: {}"),
            'conflation': _("=Conflation="),
            'osm_addresses': _("OSM addresses : {}"),
            'osm_addresses_whithout_number': _("  Without house number: {}"),
            'refused_addresses': _("Refused addresses existing in OSM: {}"),
            'osm_buildings': _("Buildings/pools in OSM: {}"),
            'osm_building_conflicts': _("Buildings/pools with conflic: {}"),
            'nodes': _("Nodes: {}"),
            'ways': _("Ways: {}"),
            'relations': _("Relations: {}"),
            'out_buildings': _('Buildings: {}'),
            'out_parts': _('Buildings parts: {}'),
            'out_pools': _('Swimming pools: {}'),
            'tasks_r': _("Rustic tasks files: {}"),
            'tasks_u': _("Urban tasks files: {}"),
            'building_types': _("Building types counter: {}"),
            'dlag': _("Max. levels above ground (level: # of buildings): {}"),
            'dlbg': _("Min. levels below ground (level: # of buildings): {}"),
            'fixmes': _("Fixmes: {}"),
            'warnings': _("Warnings:"),
        }

        self.groups = OrderedDict([
            ('head', ['mun_name', 'mun_code', 'mun_area', 'date']),
            ('input', ['address_date', 'inp_address', 'inp_address_entrance', 
                'inp_address_parcel', 'inp_zip_codes', 'inp_street_names',
                'building_date', 'inp_buildings', 'inp_parts', 'inp_pools']),
            ('process', ['addresses_without_number','orphand_addresses', 
                'multiple_addresses', 
                'orphand_parts', 'underground_parts', 'new_footprints',
                'multipart_geoms_building', 'exploded_parts_building',
                'parts_to_footprint', 'adjacent_parts',
                'geom_rings_building', 'geom_invalid_building',
                'vertex_close_building', 'vertex_topo_building',
                'vertex_simplify_building']),
            ('conflation', ['osm_addresses', 'osm_addresses_whithout_number',
                'refused_addresses', 'osm_buildings', 'osm_building_conflicts']),
            ('output', ['nodes', 'ways', 'relations', 
                'out_buildings', 'out_parts', 'out_pools', 'out_address', 
                'out_address_entrance', 'out_address_building', 'out_addr_str', 
                'out_addr_plc', 'building_types', 'dlag', 'dlbg', 'tasks_r', 
                'tasks_u', 'fixmes', 'warnings'])
        ])

    def __setattr__(self, key, value):
        if key in ['values', 'titles', 'groups']:
            super(Report, self).__setattr__(key, value)
        else:
            self.values[key] = value

    def __getattr__(self, key):
        return self.values[key]

    def to_string(self):
        output = ''
        for group_key, members in self.groups.items():
            is_void = all(k not in self.values for k in members)
            if group_key in self.titles and not is_void:
                output += setup.eol + self.titles[group_key] + setup.eol
            for mem_key in members:
                if mem_key in self.values:
                    if isinstance(self.values[mem_key], list):
                        if len(self.values[mem_key]) > 0:
                            output += self.titles[mem_key]
                            for item in self.values[mem_key]:
                                output += setup.eol + item
                            output += setup.eol
                    else:
                        output += self.titles[mem_key].format(self.values[mem_key])
                        output += setup.eol
        return output

    def to_file(self, fn, encoding=setup.encoding):
        with codecs.open(fn, "w", encoding) as fo:
            fo.write(self.to_string())
        

instance = Report()

