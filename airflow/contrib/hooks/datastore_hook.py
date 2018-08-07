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
#

import json
import time
from apiclient.discovery import build
from airflow.contrib.hooks.gcp_api_base_hook import GoogleCloudBaseHook


class DatastoreHook(GoogleCloudBaseHook):
    """
    Interact with Google Cloud Datastore. This hook uses the Google Cloud Platform
    connection.

    This object is not threads safe. If you want to make multiple requests
    simultaniously, you will need to create a hook per thread.
    """

    def __init__(self,
                 datastore_conn_id='google_cloud_datastore_default',
                 delegate_to=None):
        super(DatastoreHook, self).__init__(datastore_conn_id, delegate_to)
        # datasetId is the same as the project name
        self.dataset_id = self._get_field('project')
        self.connection = self.get_conn()

    def get_conn(self):
        """
        Returns a Google Cloud Storage service object.
        """
        http_authorized = self._authorize()
        return build('datastore', 'v1beta2', http=http_authorized)

    def allocate_ids(self, partialKeys):
        """
        Allocate IDs for incomplete keys.
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/allocateIds

        :param partialKeys: a list of partial keys
        :return: a list of full keys.
        """
        resp = self.connection.datasets().allocateIds(datasetId=self.dataset_id, body={'keys': partialKeys}).execute()
        return resp['keys']

    def begin_transaction(self):
        """
        Get a new transaction handle
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/beginTransaction

        :return: a transaction handle
        """
        resp = self.connection.datasets().beginTransaction(datasetId=self.dataset_id, body={}).execute()
        return resp['transaction']

    def commit(self, body):
        """
        Commit a transaction, optionally creating, deleting or modifying some entities.
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/commit

        :param body: the body of the commit request
        :return: the response body of the commit request
        """
        resp = self.connection.datasets().commit(datasetId=self.dataset_id, body=body).execute()
        return resp

    def lookup(self, keys, read_consistency=None, transaction=None):
        """
        Lookup some entities by key
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/lookup
        :param keys: the keys to lookup
        :param read_consistency: the read consistency to use. default, strong or eventual.
                Cannot be used with a transaction.
        :param transaction: the transaction to use, if any.
        :return: the response body of the lookup request.
        """
        body = {'keys': keys}
        if read_consistency:
            body['readConsistency'] = read_consistency
        if transaction:
            body['transaction'] = transaction
        return self.connection.datasets().lookup(datasetId=self.dataset_id, body=body).execute()

    def rollback(self, transaction):
        """
        Roll back a transaction
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/rollback
        :param transaction: the transaction to roll back
        """
        self.connection.datasets().rollback(datasetId=self.dataset_id, body={'transaction': transaction})\
            .execute()

    def run_query(self, body):
        """
        Run a query for entities.
        see https://cloud.google.com/datastore/docs/apis/v1beta2/datasets/runQuery
        :param body: the body of the query request
        :return: the batch of query results.
        """
        resp = self.connection.datasets().runQuery(datasetId=self.dataset_id, body=body).execute()
        return resp['batch']

    def get_operation(self, name):
        """
        Gets the latest state of a long-running operation

        :param name: the name of the operation resource
        """
        resp = self.connection.projects().operations().get(name=name).execute()
        return resp

    def delete_operation(self, name):
        """
        Deletes the long-running operation

        :param name: the name of the operation resource
        """
        resp = self.connection.projects().operations().delete(name=name).execute()
        return resp

    def poll_operation_until_done(self, name, polling_interval_in_seconds):
        """
        Poll backup operation state until it's completed
        """
        while True:
            result = self.get_operation(name)
            state = result['metadata']['common']['state']
            if state == 'PROCESSING':
                self.log.info('Operation is processing. Re-polling state in {} seconds'
                              .format(polling_interval_in_seconds))
                time.sleep(polling_interval_in_seconds)
            else:
                return result

    def export_to_storage_bucket(self, bucket, namespace=None, entity_filter=None, labels=None):
        """
        Export entities from Cloud Datastore to Cloud Storage for backup
        """
        output_uri_prefix = 'gs://' + '/'.join(filter(None, [bucket, namespace]))
        if not entity_filter:
            entity_filter = {}
        if not labels:
            labels = {}
        body = {
            'outputUrlPrefix': output_uri_prefix,
            'entityFilter': entity_filter,
            'labels': labels,
        }
        resp = self.admin_connection.projects().export(projectId=self.project_id, body=body).execute()
        return resp

    def import_from_storage_bucket(self, bucket, file, namespace=None, entity_filter=None, labels=None):
        """
        Import a backup from Cloud Storage to Cloud Datastore
        """
        input_url = 'gs://' + '/'.join(filter(None, [bucket, namespace, file]))
        if not entity_filter:
            entity_filter = {}
        if not labels:
            labels = {}
        body = {
            'inputUrl': input_url,
            'entityFilter': entity_filter,
            'labels': labels,
        }
        resp = self.admin_connection.projects().import_(projectId=self.project_id, body=body).execute()
        return resp
