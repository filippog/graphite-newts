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
import re

import graphite_api_app
from graphite_newts import finder
from graphite_api.node import BranchNode, LeafNode


class Query(object):
    def __init__(self, pattern, startTime=0, endTime=0):
        self.pattern = pattern
        self.startTime = startTime
        self.endTime = endTime


class FakeNewtsClient(object):
    def __init__(self, url):
        self._resources = {}
        pass

    def _parents(self, resource):
        if ':' not in resource:
            return
        parts = resource.split(':')
        for i, part in enumerate(parts):
            yield ':'.join(parts[:i])

    def _insert(self, resource, metric=None, values=None):
        for parent in self._parents(resource):
            if not parent:
                continue
            self._resources.setdefault(parent, {})
        r = self._resources.setdefault(resource, {})
        if metric:
            m = r.setdefault(metric, [])
            if values:
                m.extend(values)

    def fetch(self, resource, metric, start, end):
        pass

    def search(self, *terms):
        for term in terms:
            if term == '_tree:root':
                for r in self._resources:
                    if ':' in r:
                        continue
                    yield r, list(self._resources[r].keys())
            elif term.startswith('_parent:'):
                branch = term.split(':', 1)[1]
                for r in self._resources:
                    if not re.match('%s:[^:]+$' % branch, r):
                        continue
                    yield r, list(self._resources[r].keys())


class TestFinderQueries(graphite_api_app.TestCase):
    def setUp(self):
        super(TestFinderQueries, self).setUp()
        self.client = FakeNewtsClient('test')
        self.finder = finder.NewtsFinder(
                {'newts': {'url': 'localhost'}},
                newts_client=self.client, app=self.app)

    def _run_query(self, pattern):
        q = Query(pattern)
        results = [x for x in self.finder.find_nodes(q)]
        return [x for x in results if isinstance(x, BranchNode)], \
               [x for x in results if isinstance(x, LeafNode)]

    def testClientSelfTest(self):
        self.client._insert('r1:r2:r3:r4', 'metric1')
        for resource, metrics in self.client.search('_tree:root'):
            self.assertEqual(len(metrics), 0)
            self.assertEqual(resource, 'r1')

        for resource, metrics in self.client.search('_parent:r1'):
            self.assertEqual(len(metrics), 0)
            self.assertEqual(resource, 'r1:r2')

        for resource, metrics in self.client.search(r'_parent:r1\:r2'):
            self.assertEqual(len(metrics), 0)
            self.assertEqual(resource, 'r1:r2:r3')

        self.client._insert('r1', 'metric1')
        self.client._insert('r1')
        self.client._insert('r1:r2')
        self.client._insert('r1:r2:r3', 'metric1')
        self.client._insert('r1:r2:r3', 'metric2')
        for resource, metrics in self.client.search(r'_parent:r1\:\r2'):
            self.assertEqual(len(metrics), 2)
            self.assertEqual(resource, 'r1:r2:r3')

    def testNestedQuery(self):
        self.client._insert('r1:r2:r3:r4', 'metric1')
        self.client._insert('r1:r2:r3:r4', 'metric2')
        self.client._insert('r1:r2:r3:r4', 'metric3')
        self.client._insert('r1:r2:r3', 'nomatch')
        self.client._insert('bogus:path', 'metric3')

        branch, leaf = self._run_query('r1.r2.r3.r4.metric*')
        self.assertEqual(len(leaf), 3)
        self.assertEqual(len(branch), 0)

    def testRootQuery(self):
        self.client._insert('foo:bar:baz')
        self.client._insert('zomg')
        self.client._insert('toplevel2')
        self.client._insert('toplevel3', 'metric1')
        self.client._insert('toplevel4:branch1', 'metric2')

        branch, leaf = self._run_query('*')
        print branch, leaf
        self.assertEqual(len(branch), 5)
        self.assertEqual(len(leaf), 0)

    def testSingleNodeQuery(self):
        self.client._insert('foo:bar:baz')
        self.client._insert('foo:meh')
        self.client._insert('foo')
        self.client._insert('foo', 'metric')
        self.client._insert('nomatch')

        branch, leaf = self._run_query('foo')
        self.assertEqual(len(branch), 1)
        self.assertEqual(len(leaf), 0)

        branch, leaf = self._run_query('foo.*')
        print branch, leaf
        self.assertEqual(len(branch), 2)
        self.assertEqual(len(leaf), 1)

    def testRecursionQuery(self):
        self.client._insert('branch1:branch2', 'leaf2')
        self.client._insert('branch1:branch2', 'leaf2')
        self.client._insert('branch1')
        self.client._insert('branch1', 'leaf1')
        self.client._insert('branch2')
        self.client._insert('branch2:branch3')
        self.client._insert('branch2:branch4:branch5', 'leaf4')
        self.client._insert('branch2:branch4:branch6', 'leaf4')

        branch, leaf = self._run_query('branch1.*')
        self.assertEqual(len(branch), 1)
        self.assertEqual(len(leaf), 1)

        branch, leaf = self._run_query('branch2.*.branch6.leaf*')
        self.assertEqual(len(branch), 0)
        self.assertEqual(len(leaf), 1)

        branch, leaf = self._run_query('branch2.branch4.*')
        self.assertEqual(len(branch), 2)
        self.assertEqual(len(leaf), 0)

        branch, leaf = self._run_query('branch2.*')
        self.assertEqual(len(branch), 2)
        self.assertEqual(len(leaf), 0)

    def testNoResultQuery(self):
        self.client._insert('foo:bar:baz')
        self.client._insert('toplevel3', 'metric1')
        self.client._insert('toplevel3', 'metric2')
        self.client._insert('toplevel4', 'metric')

        branch, leaf = self._run_query('notfound.*')
        print branch, leaf
        self.assertEqual(len(branch), 0)
        self.assertEqual(len(leaf), 0)

        branch, leaf = self._run_query('not.found.here.*')
        self.assertEqual(len(branch), 0)
        self.assertEqual(len(leaf), 0)

    # XXX improve
    def testWildcard(self):
        self.client._insert('l1:foo', 'metric1')
        self.client._insert('l1:bar', 'metric2')
        self.client._insert('l1:baz', 'metric3')
        self.client._insert('l1:baz:doh', 'metric1')

        branch, leaf = self._run_query('l1.*.metric1')
        self.assertEqual(len(branch), 0)
        self.assertEqual(len(leaf), 1)

        self.client._insert('l2:foo:meh', 'metric2')
        self.client._insert('l2:bar:moz')
        self.client._insert('l2:baz:gah')

        branch, leaf = self._run_query('l2.*.m*')
        self.assertEqual(len(branch), 2)
        self.assertEqual(len(leaf), 0)


if __name__ == '__main__':
    unittest.main()
