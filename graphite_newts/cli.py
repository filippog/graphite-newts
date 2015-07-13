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

import datetime
import logging
import math
import os

import click
import parsedatetime
from . import client as newts


DEBUG = False


@click.group()
@click.option('--debug/--no-debug', default=False)
def main(debug):
    global DEBUG
    logging_level = logging.INFO
    if debug:
        DEBUG = True
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level)


@main.command(name='newts-fetch')
@click.option('--url', default='http://localhost:8080', show_default=True)
@click.option('--start', default='-15m', show_default=True)
@click.option('--end', default='now', show_default=True)
@click.option('--resolution', default='1m', show_default=True)
@click.option('--maxpoints', default=None, type=int, show_default=True,
        metavar='NUM', help="Fetch (close to) NUM datapoints, regardless of resolution")
@click.argument('resource')
@click.argument('metric')
def newts_fetch(url, resource, metric, start, end, resolution, maxpoints):
    client = newts.NewtsClient(url)

    cal = parsedatetime.Calendar()
    time_start = cal.parseDT(start)[0]
    time_end = cal.parseDT(end)[0]
    ts_start = int(time_start.strftime('%s'))
    ts_end = int(time_end.strftime('%s'))

    if maxpoints is not None:
        resolution_seconds = int((ts_end - ts_start) / maxpoints)
    else:
        now = datetime.datetime.now()
        resolution_parsed = cal.parseDT(resolution, sourceTime=now)[0]
        resolution_seconds = int(math.ceil((resolution_parsed -
            now).total_seconds()))

    datapoints = client.fetch(resource, metric,
            ts_start, ts_end, resolution_seconds)
    for timestamp, value in datapoints:
        print(timestamp, value)


@main.command()
@click.option('--address', default='127.0.0.1')
@click.option('--port', default=8888, type=int)
@click.option('--config', default='graphite-api.yaml', type=click.Path(exists=True))
def server(address, port, config):
    click.echo('starting development server with configuration %s' % os.path.abspath(config))
    os.environ['GRAPHITE_API_CONFIG'] = config
    os.environ['DEBUG'] = str(DEBUG)
    import graphite_api
    graphite_api.DEBUG = DEBUG
    from graphite_api.app import app
    app.run(debug=DEBUG, port=port, host=address)
