# -*- coding: utf-8 -*-
import unittest
import logging
import gettext

import setup
import hgwnames

logging.disable(logging.WARNING)
if setup.platform.startswith('win'):
    if os.getenv('LANG') is None:
        os.environ['LANG'] = setup.language
gettext.install(setup.app_name.lower(), localedir=setup.localedir)


class TestHgwnames(unittest.TestCase):

    def test_parse(self):
        names = {
            "   CL  FOO BAR  TAZ  ": "Calle Foo Bar Taz",
            u"AV DE ESPAÑA": u"Avenida de España",
            "CJ GATA (DE LA)": u"Calleja/Callejón Gata (de la)",
            "CR CUMBRE,DE LA": "Carretera/Carrera Cumbre, de la",
            "CL HILARIO (ERAS LAS)": "Calle Hilario (Eras las)",
            "CL BASTIO D'EN SANOGUERA": "Calle Bastio d'en Sanoguera",
            "CL BANC DE L'OLI": "Calle Banc de l'Oli",
            "DS ARANJASSA,S'": "Diseminados Aranjassa, s'",
            u"CL AIGUA DOLÇA (L')": u"Calle Aigua Dolça (l')",
            u"CL RUL·LAN": u"Calle Rul·lan",
        }
        for (inp, out) in names.items():
            self.assertEquals(hgwnames.parse(inp), out)


