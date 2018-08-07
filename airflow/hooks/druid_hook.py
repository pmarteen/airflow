# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import print_function

import requests
import time

from pydruid.client import PyDruid
import requests

from airflow.hooks.base_hook import BaseHook
from airflow.exceptions import AirflowException

LOAD_CHECK_INTERVAL = 5
DEFAULT_TARGET_PARTITION_SIZE = 5000000


    :param druid_ingest_conn_id: The connection id to the Druid overlord machine which accepts index jobs
    :type druid_ingest_conn_id: string
    :param timeout: The interval between polling the Druid job for the status of the ingestion job
    :type timeout: int
    :param max_ingestion_time: The maximum ingestion time before assuming the job failed
    :type max_ingestion_time: int
    """
    def __init__(
            self,
            druid_query_conn_id='druid_query_default',
            druid_ingest_conn_id='druid_ingest_default'):
        self.druid_query_conn_id = druid_query_conn_id
        self.druid_ingest_conn_id = druid_ingest_conn_id
        self.header = {'content-type': 'application/json'}

    def get_conn(self):
        """
        Returns a druid connection object for query
        """
        conn = self.get_connection(self.druid_query_conn_id)
        return PyDruid(
            "http://{conn.host}:{conn.port}".format(**locals()),
            conn.extra_dejson.get('endpoint', ''))

    @property
    def ingest_post_url(self):
        conn = self.get_connection(self.druid_ingest_conn_id)
        host = conn.host
        port = conn.port
        endpoint = conn.extra_dejson.get('endpoint', '')
        return "http://{host}:{port}/{endpoint}".format(**locals())

    def submit_indexing_job(self, json_index_spec):
        url = self.get_conn_url()

        req_index = requests.post(url, json=json_index_spec, headers=self.header)
        if req_index.status_code != 200:
            raise AirflowException('Did not get 200 when '
                                   'submitting the Druid job to {}'.format(url))

        req_json = req_index.json()
        # Wait until the job is completed
        druid_task_id = req_json['task']

        running = True

        sec = 0
        while running:
            req_status = requests.get("{0}/{1}/status".format(url, druid_task_id))

            self.log.info("Job still running for %s seconds...", sec)

            sec = sec + 1

            if sec > self.max_ingestion_time:
                raise AirflowException('Druid ingestion took more than %s seconds', self.max_ingestion_time)

            time.sleep(self.timeout)

            status = req_status.json()['status']['status']
            if status == 'RUNNING':
                running = True
            elif status == 'SUCCESS':
                running = False  # Great success!
            elif status == 'FAILED':
                raise AirflowException('Druid indexing job failed, check console for more info')
            else:
                raise AirflowException('Could not get status of the job, got %s', status)

        self.log.info('Successful index')
