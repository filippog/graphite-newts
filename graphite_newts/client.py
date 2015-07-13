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

import json
from datetime import datetime

import requests

from structlog import get_logger
logger = get_logger()


class NewtsClient(object):
    def __init__(self, url):
        self.url = url

    def _format_date(self, date):
        return datetime.fromtimestamp(float(date)).strftime('%Y-%m-%dT%H:%M:%S.000Z')

    def fetch(self, resource, metric, start, end, resolution,
            function='AVERAGE'):

        resolution = '{}s'.format(resolution)
        result_descriptor = {
            'interval': '30s',
            'exports': [metric],
            'datasources': [{
                 'label': metric,
                 'source': metric,
                 'function': function,
                 'heartbeat': '1m'
             }],
        }

        fetch_params = {
            'resolution': resolution,
            'start': self._format_date(start),
            'end': self._format_date(end),
        }

        headers = {
            'Content-Type': 'application/json',
        }

        request_url = '{}/measurements/{}'.format(self.url, resource)
        logger.debug('fetch', url=request_url, data=result_descriptor,
                params=fetch_params)
        data = requests.post(request_url,
                data=json.dumps(result_descriptor),
                params=fetch_params,
                headers=headers)

        try:
            data.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.warn('error while executing %r: %r' % (data.url, e))
            raise e

        for group in data.json():
            d = group[0]
            try:
                yield d['timestamp'], float(d['value'])
            except ValueError:
                continue

    def search(self, *terms):
        logger.debug("search", url=self.url, terms=terms)

        search_params = 'q=%s' % ' AND '.join(terms)
        try:
            response = requests.get(self.url + '/search', params=search_params)
            response.raise_for_status()
            for result in response.json():
                yield result['resource']['id'], result['metrics']
        except requests.exceptions.HTTPError as e:
            logger.warn("search_error", exception=e)
