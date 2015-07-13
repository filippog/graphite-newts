#   Copyright (C) 2015 Filippo Giunchedi
#                 2015 Wikimedia Foundation
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import math

import requests
import requests_mock
from graphite_newts.client import NewtsClient

NEWTS_URL = 'http://localhost:8080'


@requests_mock.Mocker()
class TestNewtsFetch(unittest.TestCase):
    def setUp(self):
        self.client = NewtsClient(NEWTS_URL)

    def testFetch(self, m):
        datapoints = [
                [{"timestamp": 1, "value": "NaN"}],
                [{"timestamp": 2, "value": -5}],
                [{"timestamp": 3, "value": 0.4}],
            ]
        m.post('/measurements/foo:bar?resolution=60s',
               json=datapoints)
        result = {x: y for x, y in self.client.fetch('foo:bar', 'metric',
                0, 86400, 60)}
        self.assertTrue(any([math.isnan(x) for x in list(result.values())]))
        self.assertIn(-5, list(result.values()))
        self.assertIn(0.4, list(result.values()))


if __name__ == '__main__':
    unittest.main()
