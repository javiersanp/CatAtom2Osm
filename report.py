# -*- coding: utf-8 -*-
"""Statistics report"""

from collections import OrderedDict
from datetime import datetime
import codecs

import setup

class Report(object):

    def __init__(self):
        self.values = {'date': datetime.now().strftime('%x')}
        self.titles = OrderedDict([
            ('mun_name', _('Municipality: {}')),
            ('mun_code', _('Code: {}')),
            ('mun_area', _(u'Area: {} km²')),
            ('date', _('Date: {}')),
            ('group_address', _('Addresses')),
            ('subgroup_ad_input', _('Input data')),
            ('address_date', _('Source date: {}')),
            ('inp_address', _('Feature count: {}')),
            ('inp_address_entrance', _('  Type entrance: {}')),
            ('inp_address_parcel', _('  Type parcel: {}')),
            ('inp_zip_codes', _('Postal codes: {}')),
            ('inp_street_names', _('Street names: {}')),
            ('subgroup_ad_process', _('Process')),
            ('addresses_without_number', _('Addresses without house number deleted: {}')),
            ('orphand_addresses', _('Addresses without associated building deleted: {}')),
            ('multiple_addresses', _('Addresses belonging to multiple buildings deleted: {}')),
            ('subgroup_ad_conflation', _("Conflation")),
            ('osm_addresses', _("OSM addresses : {}")),
            ('osm_addresses_whithout_number', _("  Without house number: {}")),
            ('refused_addresses', _("Refused addresses existing in OSM: {}")),
            ('subgroup_ad_output', _('Output data')),
            ('out_address', _('Addresses: {}')),
            ('out_address_entrance', _('  In entrance nodes: {}')),
            ('out_address_building', _('  In buildings: {}')),
            ('out_addr_str', _('  Type addr:street: {}')),
            ('out_addr_plc', _('  Type addr:place: {}')),
            ('group_buildings', _('Buildings')),
            ('subgroup_bu_input', _('Input data')),
            ('building_date', _('Source date: {}')),
            ('inp_features', _('Feature count: {}')),
            ('inp_buildings', '  ' + _('Edificios: {}')),
            ('inp_parts', '  ' + _('Buildings parts: {}')),
            ('inp_pools', '  ' + _('Swimming pools: {}')),
            ('subgroup_bu_process', _('Process')),
            ('orphand_parts', _("Parts outside footprint deleted: {}")),
            ('underground_parts', _("Parts with no floors above ground: {}")),
            ('new_footprints', _("Building footprints created: {}")),
            ('multipart_geoms_building', _("Buildings with multipart geometries: {}")),
            ('exploded_parts_building', _("Buildings resulting from spliting multiparts: {}")),
            ('parts_to_footprint', _("Parts merged to the footprint: {}")),
            ('adjacent_parts', _("Adjacent parts merged: {}")),
            ('geom_rings_building', _('Invalid geometry rings deleted: {}')),
            ('geom_invalid_building', _('Invalid geometries deleted: {}')),
            ('vertex_close_building', _('Close vertices merged: {}')),
            ('vertex_topo_building', _('Topological points created: {}')),
            ('vertex_simplify_building', _("Simplified vertices: {}")),
            ('subgroup_bu_conflation', _("Conflation")),
            ('osm_buildings', _("Buildings/pools in OSM: {}")),
            ('osm_building_conflicts', _("Buildings/pools with conflic: {}")),
            ('subgroup_bu_output', _('Output data')),
            ('nodes', _("Nodes: {}")),
            ('ways', _("Ways: {}")),
            ('relations', _("Relations: {}")),
            ('out_buildings', _('Buildings: {}')),
            ('out_parts', _('Buildings parts: {}')),
            ('out_pools', _('Swimming pools: {}')),
            ('building_types', _("Building types counter: {}")),
            ('dlag', _("Max. levels above ground (level: # of buildings): {}")),
            ('dlbg', _("Min. levels below ground (level: # of buildings): {}")),
            ('tasks_r', _("Rustic tasks files: {}")),
            ('tasks_u', _("Urban tasks files: {}")),
            ('group_problems', _("Problems")),
            ('fixmes', _("Fixmes: {}")),
            ('warnings', _("Warnings:")),
        ])

    def __setattr__(self, key, value):
        if key in ['values', 'titles', 'groups']:
            super(Report, self).__setattr__(key, value)
        else:
            self.values[key] = value

    def __getattr__(self, key):
        return self.values[key]

    def to_string(self):
        groups = set()
        last_group = False
        last_subgroup = False
        for key in self.titles.keys():
            exists = key in self.values
            if exists and isinstance(self.values[key], list) and len(self.values[key]) == 0:
                exists = False
            if key.startswith('group_'):
                last_group = key
                last_subgroup = False
            elif key.startswith('subgroup_'):
                last_subgroup = key
            if last_group and exists:
                groups.add(last_group)
            if last_subgroup and exists:
                groups.add(last_subgroup)
        output = ''
        for key, title in self.titles.items():
            if key.startswith('group_') and key in groups:
                output += setup.eol + '=' + self.titles[key] + '=' + setup.eol
            elif key.startswith('subgroup_') and key in groups:
                output += setup.eol + '==' + self.titles[key] + '==' + setup.eol
            elif key in self.values:
                if isinstance(self.values[key], list):
                    if len(self.values[key]) > 0:
                        output += title
                        for item in self.values[key]:
                            output += setup.eol + item
                        output += setup.eol
                else:
                    output += title.format(self.values[key])
                    output += setup.eol
        return output

    def to_file(self, fn, encoding=setup.encoding):
        with codecs.open(fn, "w", encoding) as fo:
            fo.write(self.to_string())
        

instance = Report()

