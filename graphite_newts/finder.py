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


import time
import re
import math

from structlog import get_logger

from graphite_api.intervals import Interval, IntervalSet
from graphite_api.node import BranchNode, LeafNode
from graphite_api.app import app
from graphite_api.finders import match_entries

from . import client

logger = get_logger()


class NewtsReader(object):
    __slots__ = ('resource', 'metric', 'client', 'maxpoints')

    def __init__(self, client, resource, metric, maxpoints):
        self.resource = resource
        self.metric = metric
        self.client = client
        self.maxpoints = maxpoints

    def get_intervals(self):
        start = float('-inf')
        end = float('inf')
        logger.debug("get_intervals", finder="newts", start=start, end=end)
        return IntervalSet([Interval(start, end)])

    def fetch(self, time_start, time_end):
        logger.debug("fetch", reader="newts", client=self.client,
                     resource=self.resource, metric=self.metric,
                     start=time_start, end=time_end)

        values = []
        ts_start = time.time()
        ts_end = 0

        # XXX
        resolution = int((time_end - time_start) / self.maxpoints)
        resolution = (resolution // 60) * 60
        if resolution < 60:
            resolution = 60
        for timestamp_ms, value in self.client.fetch(
                self.resource, self.metric, time_start, time_end, resolution):
            timestamp = timestamp_ms / 1000
            ts_start = min(ts_start, timestamp)
            ts_end = max(ts_end, timestamp)
            if math.isnan(value):
                values.append(None)
            else:
                values.append(value)

        time_info = (ts_start, ts_end, resolution)
        return time_info, values


class NewtsFinder(object):
    DEFAULT_CONFIG = {'url': 'http://localhost:8080',
                      'fetch.maxpoints': 200}

    def __init__(self, app_config, newts_client=None, app=app):
        self.config = self.DEFAULT_CONFIG.copy()
        self.config.update(app_config.get('newts', {}))
        self.use_cache = app_config.get('cache') is not None
        self.app = app

        if newts_client is not None:
            self.client = newts_client
        else:
            self.client = client.NewtsClient(self.config['url'])

    def find_nodes(self, query):
        logger.debug("find_nodes", finder="newts", start=query.startTime,
                     end=query.endTime, pattern=query.pattern)

        for resource, metric, is_leaf in self._search_nodes(query.pattern):
            # XXX ambigous, : is valid in graphite name
            dot_path = resource.replace(':', '.')
            if not is_leaf:
                yield BranchNode(dot_path)
            else:
                reader = NewtsReader(self.client, resource, metric,
                                     self.config['fetch.maxpoints'])
                yield LeafNode('{}.{}'.format(dot_path, metric), reader)

    # XXX potentially big results
    def _run_search(self, term):
        if not self.use_cache:
            result = self.client.search(term)
        else:
            result = self.app.cache.get(term)
            if result is None:
                result = [(x, y) for x, y in self.client.search(term)]
                self.app.cache.add(term, result)

        for x, y in result:
            yield x, y

    def _search_nodes(self, pattern):
        parts = pattern.split('.')
        queue = [('_parent:_root', parts)]

        while queue:
            search_term, patterns = queue.pop()
            pattern = patterns[0]
            patterns = patterns[1:]

            # map branches to their resource (the branch full path) and the
            # retrieved metrics (the leaves)
            branches = {}
            for resource, metrics in self._run_search(search_term):
                if search_term == '_parent:_root':
                    branch = resource
                else:
                    # XXX column is valid in graphite names
                    branch = resource.rsplit(':', 1)[1]
                branches[branch] = (resource, metrics)

            # multi-part pattern
            if patterns:
                # walk the branches first
                for match in match_entries(branches.keys(), pattern):
                    resource, metrics = branches[match]
                    parent_term = resource.replace(':', '\:')
                    parent_term = parent_term.replace('-', '\-')
                    queue.append(('_parent:%s' % parent_term, patterns))
                    # only one pattern left, match leaves too (i.e. metrics)
                    if len(patterns) == 1:
                        for match in match_entries(metrics, patterns[0]):
                            yield resource, match, True
            else:
                # patterns like 'foo', yield only branches
                for match in match_entries(branches.keys(), pattern):
                    yield match, None, False

    # XXX fix regex transformation
    # XXX untrusted input
    # https://graphite.readthedocs.org/en/latest/render_api.html
    def _compile_part(self, part):
        pattern = part.replace('*', '.*')
        pattern = pattern.replace('{', '(')
        pattern = pattern.replace('}', ')')
        pattern = pattern.replace(',', '|')
        logger.debug('_compile_part', pattern=pattern, part=part)
        return re.compile(pattern)
