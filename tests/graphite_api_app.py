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

import os
import shutil
import sys
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest


TMP_DIR = tempfile.mkdtemp()
CONFIG_FILE = tempfile.mkstemp(dir=TMP_DIR)[1]
INDEX_FILE = tempfile.mkstemp(dir=TMP_DIR)[1]

config = {
    'search_index': TMP_DIR,
    'path': TMP_DIR,
}
with open(CONFIG_FILE, 'w') as f:
    f.write('path: %s\nsearch_index: %s\n' % (TMP_DIR, INDEX_FILE))

os.environ.setdefault('GRAPHITE_API_CONFIG', CONFIG_FILE)
from graphite_api.app import app


null_handler = 'logging.NullHandler'
if sys.version_info > (2, 7):
    from logging.config import dictConfig
else:
    from logutils.dictconfig import dictConfig

    class NullHandler(object):
        def emit(self, record):
            pass

        def setLevel(self, level):
            pass
    null_handler = 'tests.NullHandler'

dictConfig({
    'version': 1,
    'handlers': {
        'raw': {
            'level': 'DEBUG',
            'class': null_handler,
        },
    },
})


class TestCase(unittest.TestCase):
    def _cleanup(self):
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    def setUp(self):
        self._cleanup()
        app.config['TESTING'] = True
        self.app = app.test_client()

    def tearDown(self):
        self._cleanup()
