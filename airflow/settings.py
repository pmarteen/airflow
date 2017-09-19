# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import sys

from datadog import dogstatsd
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from airflow import configuration as conf
from airflow.utils.log.logging_mixin import LoggingMixin

log = LoggingMixin().log

class BaseStatsLogger(object):

    @classmethod
    def incr(cls, stat, count=1, rate=1, tags=()):
        pass

    @classmethod
    def decr(cls, stat, count=1, rate=1, tags=()):
        pass

    @classmethod
    def gauge(cls, stat, value, rate=1, delta=False, tags=()):
        pass

    @classmethod
    def timing(cls, stat, dt, tags=()):
        pass

    @classmethod
    def set(cls, stat, value, tags=(), rate=1):
        pass

Stats = BaseStatsLogger


class DogStatsWrapper(BaseStatsLogger):
    def __init__(self, host, port, prefix):
        self.stats_client = dogstatsd.DogStatsd(host, port)
        self.prefix = prefix

    def incr(self, stat, count=1, rate=1, tags=()):
        self.stats_client.increment('{}.{}'.format(self.prefix, stat), count, sample_rate=rate, tags=tags)

    def decr(self, stat, count=1, rate=1, tags=()):
        self.stats_client.decrement('{}.{}'.format(self.prefix, stat), count, sample_rate=rate, tags=tags)

    def gauge(self, stat, value, rate=1, delta=False, tags=()):
        self.stats_client.gauge('{}.{}'.format(self.prefix, stat), value, sample_rate=rate, tags=tags)

    def timing(self, stat, dt, tags=()):
        self.stats_client.timing('{}.{}'.format(self.prefix, stat), dt, tags=tags)

    def set(self, stat, value, tags=(), rate=1):
        self.stats_client.set('{}.{}'.format(self.prefix, stat), value, tags=tags, sample_rate=rate)


if conf.getboolean('scheduler', 'statsd_on'):
    statsd = DogStatsWrapper(
        host=conf.get('scheduler', 'statsd_host'),
        port=conf.getint('scheduler', 'statsd_port'),
        prefix=conf.get('scheduler', 'statsd_prefix'))
    Stats = statsd
else:
    Stats = BaseStatsLogger


HEADER = """\
  ____________       _____________
 ____    |__( )_________  __/__  /________      __
____  /| |_  /__  ___/_  /_ __  /_  __ \_ | /| / /
___  ___ |  / _  /   _  __/ _  / / /_/ /_ |/ |/ /
 _/_/  |_/_/  /_/    /_/    /_/  \____/____/|__/
 """

BASE_LOG_URL = '/admin/airflow/log'
LOGGING_LEVEL = logging.INFO

# the prefix to append to gunicorn worker processes after init
GUNICORN_WORKER_READY_PREFIX = "[ready] "

# can't move this to conf due to ConfigParser interpolation
LOG_FORMAT = (
    '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
LOG_FORMAT_WITH_PID = (
    '[%(asctime)s] [%(process)d] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
LOG_FORMAT_WITH_THREAD_NAME = (
    '[%(asctime)s] {%(filename)s:%(lineno)d} %(threadName)s %(levelname)s - %(message)s')
SIMPLE_LOG_FORMAT = '%(asctime)s %(levelname)s - %(message)s'

AIRFLOW_HOME = None
SQL_ALCHEMY_CONN = None
DAGS_FOLDER = None

engine = None
Session = None


def policy(task_instance):
    """
    This policy setting allows altering task instances right before they
    are executed. It allows administrator to rewire some task parameters.

    Note that the ``TaskInstance`` object has an attribute ``task`` pointing
    to its related task object, that in turns has a reference to the DAG
    object. So you can use the attributes of all of these to define your
    policy.

    To define policy, add a ``airflow_local_settings`` module
    to your PYTHONPATH that defines this ``policy`` function. It receives
    a ``TaskInstance`` object and can alter it where needed.

    Here are a few examples of how this can be useful:

    * You could enforce a specific queue (say the ``spark`` queue)
        for tasks using the ``SparkOperator`` to make sure that these
        task instances get wired to the right workers
    * You could force all task instances running on an
        ``execution_date`` older than a week old to run in a ``backfill``
        pool.
    * ...
    """
    pass


def configure_logging(log_format=LOG_FORMAT):

    def _configure_logging(logging_level):
        global LOGGING_LEVEL
        logging.root.handlers = []
        logging.basicConfig(
            format=log_format, stream=sys.stdout, level=logging_level)
        LOGGING_LEVEL = logging_level

    if "logging_level" in conf.as_dict()["core"]:
        logging_level = conf.get('core', 'LOGGING_LEVEL').upper()
    else:
        logging_level = LOGGING_LEVEL
    try:
        _configure_logging(logging_level)
    except ValueError:
        logging.warning(
            "Logging level %s is not defined. Use default.", logging_level
        )
        _configure_logging(logging.INFO)


def configure_vars():
    global AIRFLOW_HOME
    global SQL_ALCHEMY_CONN
    global DAGS_FOLDER
    AIRFLOW_HOME = os.path.expanduser(conf.get('core', 'AIRFLOW_HOME'))
    SQL_ALCHEMY_CONN = conf.get('core', 'SQL_ALCHEMY_CONN')
    DAGS_FOLDER = os.path.expanduser(conf.get('core', 'DAGS_FOLDER'))


def configure_orm(disable_connection_pool=False):
    global engine
    global Session
    engine_args = {}
    if disable_connection_pool:
        engine_args['poolclass'] = NullPool
    elif 'sqlite' not in SQL_ALCHEMY_CONN:
        # Engine args not supported by sqlite
        engine_args['pool_size'] = conf.getint('core', 'SQL_ALCHEMY_POOL_SIZE')
        engine_args['pool_recycle'] = conf.getint('core',
                                                  'SQL_ALCHEMY_POOL_RECYCLE')

    engine = create_engine(SQL_ALCHEMY_CONN, **engine_args)
    Session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine))

try:
    from airflow_local_settings import *
    log.info("Loaded airflow_local_settings.")
except:
    pass

configure_logging()
configure_vars()
configure_orm()

# TODO: Unify airflow logging setups. Please see AIRFLOW-1457.
logging_config_path = conf.get('core', 'logging_config_path')
try:
    from logging_config_path import LOGGING_CONFIG
    log.debug("Successfully imported user-defined logging config.")
except Exception as e:
    # Import default logging configurations.
    log.debug(
        "Unable to load custom logging config file: %s. Using default airflow logging config instead",
        e
    )
    from airflow.config_templates.default_airflow_logging import \
        DEFAULT_LOGGING_CONFIG as LOGGING_CONFIG
logging.config.dictConfig(LOGGING_CONFIG)

# Const stuff

KILOBYTE = 1024
MEGABYTE = KILOBYTE * KILOBYTE
WEB_COLORS = {'LIGHTBLUE': '#4d9de0'}
