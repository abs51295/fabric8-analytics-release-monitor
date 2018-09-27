"""Default configuration values."""
import os

NPM_URL = os.environ.get('NPM_URL', 'https://registry.npmjs.org/')
PYPI_URL = os.environ.get('PYPI_URL', 'https://pypi.org/')
ENABLE_SCHEDULING = os.environ.get('ENABLE_SCHEDULING', '1')\
                    in ('1', 'True', 'true')
PROBE_FILE_LOCATION = "/tmp/release_monitoring/liveness.txt"
SLEEP_INTERVAL = os.environ.get('SLEEP_INTERVAL', 20)
