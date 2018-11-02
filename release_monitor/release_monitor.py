#!/usr/bin/env python3

"""The release monitor project."""

import json
import logging
import os
import signal
import sys
import time

import feedparser
import psutil
import requests
from f8a_worker.setup_celery import init_celery, init_selinon
from selinon import run_flow

from release_monitor.defaults import NPM_URL, PYPI_URL, ENABLE_SCHEDULING, \
    PROBE_FILE_LOCATION, SLEEP_INTERVAL

logger = logging.getLogger(__name__)


class ReleaseMonitor():
    """Class which check rss feeds for new releases."""

    def __init__(self):
        """Constructor."""
        self.log = logging.getLogger(__name__)
        formatter = logging.Formatter('%(asctime)s - '
                                      '%(name)s - %(levelname)s'
                                      ' - %(message)s')
        logging_handler = logging.StreamHandler(sys.stdout)
        logging_handler.setFormatter(formatter)
        self.log.addHandler(logging_handler)
        self.log.level = logging.DEBUG
        self.old_npm_feed = None
        self.npm_feed = feedparser.parse(NPM_URL + "-/rss")
        self.old_pypi_feed = None
        self.pypi_feed = feedparser.parse(PYPI_URL + "rss/updates.xml")

        if ENABLE_SCHEDULING:
            init_celery(result_backend=False)
            init_selinon()

    def run_package_analisys(self, name, ecosystem, version):
        """Run Selinon flow for analyses.

        :param name: name of the package to analyse
        :param version: package version
        :param ecosystem: package ecosystem
        :return: dispatcher ID serving flow
        """
        node_args = {
            'ecosystem': ecosystem,
            'name': name,
            'version': version,
            'recursive_limit': 0
        }

        self.log.info("Scheduling Selinon flow '%s' "
                      "with node_args: '%s'", 'bayesianFlow', node_args)
        return run_flow('bayesianFlow', node_args)

    def entry_not_in_previous_npm_set(self, entry):
        """Check if the RSS entry has been in the old npm feed."""
        if self.old_npm_feed is None:
            return True

        if entry in self.old_npm_feed:
            return False
        else:
            return True

    def entry_not_in_previous_pypi_set(self, entry):
        """Check if the RSS entry has been in the old pypi feed."""
        if self.old_pypi_feed is None:
            return True

        if entry in self.old_pypi_feed:
            return False
        else:
            return True

    def renew_rss_feeds(self):
        """Fetch new RSS feed and save the old one for comparison."""
        if sorted(self.old_pypi_feed.entries) == \
                sorted(self.pypi_feed.entries):
            self.pypi_feed = feedparser.parse(PYPI_URL + "rss/updates.xml")
        else:
            self.old_pypi_feed = self.pypi_feed

        if sorted(self.old_npm_feed.entries) == sorted(self.npm_feed.entries):
            self.npm_feed = feedparser.parse(NPM_URL + "-/rss")
        else:
            self.old_pypi_feed = self.pypi_feed

    def create_liveness_probe(self):
        """Liveness probe."""
        if os.path.isfile(PROBE_FILE_LOCATION):
            os.remove(PROBE_FILE_LOCATION)
        else:
            probe = os.path.dirname(PROBE_FILE_LOCATION)
            if not os.path.exists(probe):
                os.makedirs(probe)

        return True

    def run(self):
        """Run the monitor."""
        self.create_liveness_probe()
        self.log.info("Registered signal handler for liveness probe")

        while True:
            for i in self.npm_feed.entries:
                package_name = i['title']
                package_url = NPM_URL + "-/package/{package_name}" \
                                        "/dist-tags".format(
                                            package_name=package_name)
                package_latest_version = json.loads(
                    requests.get(package_url,
                                 headers={'content-type':
                                          'application/json'}).text)
                self.log.info("Processing "
                              "package from npm: '%s':'%s'", package_name,
                              package_latest_version.get('latest'))
                if ENABLE_SCHEDULING and self.entry_not_in_previous_npm_set(i):
                    self.run_package_analisys(package_name,
                                              'npm',
                                              package_latest_version)

            for i in self.pypi_feed.entries:
                package_name, package_latest_version = i['title'].split(' ')
                self.log.info("Processing package from pypi: '%s':'%s'",
                              package_name, package_latest_version)
                if ENABLE_SCHEDULING and \
                        self.entry_not_in_previous_pypi_set(i):
                    self.run_package_analisys(package_name,
                                              'pypi', package_latest_version)

        self.renew_rss_feeds()
        sleep(60*SLEEP_INTERVAL)
