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
"""
LocalExecutor runs tasks by spawning processes in a controlled fashion in different
modes. Given that BaseExecutor has the option to receive a `parallelism` parameter to
limit the number of process spawned, when this parameter is `0` the number of processes
that LocalExecutor can spawn is unlimited.

The following strategies are implemented:
1. Unlimited Parallelism (self.parallelism == 0): In this strategy, LocalExecutor will
spawn a process every time `execute_async` is called, that is, every task submitted to the
LocalExecutor will be executed in its own process. Once the task is executed and the
result stored in the `result_queue`, the process terminates. There is no need for a
`task_queue` in this approach, since as soon as a task is received a new process will be
allocated to the task. Processes used in this strategy are of class LocalWorker.

2. Limited Parallelism (self.parallelism > 0): In this strategy, the LocalExecutor spawns
the number of processes equal to the value of `self.parallelism` at `start` time,
using a `task_queue` to coordinate the ingestion of tasks and the work distribution among
the workers, which will take a task as soon as they are ready. During the lifecycle of
the LocalExecutor, the worker processes are running waiting for tasks, once the
LocalExecutor receives the call to shutdown the executor a poison token is sent to the
workers to terminate them. Processes used in this strategy are of class QueuedLocalWorker.

Arguably, `SequentialExecutor` could be thought as a LocalExecutor with limited
parallelism of just 1 worker, i.e. `self.parallelism = 1`.
This option could lead to the unification of the executor implementations, running
locally, into just one `LocalExecutor` with multiple modes.
"""

import multiprocessing
import subprocess
import time

from builtins import range

from airflow import configuration
from airflow.executors.base_executor import BaseExecutor
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.state import State

PARALLELISM = configuration.get('core', 'PARALLELISM')


class LocalWorker(multiprocessing.Process, LoggingMixin):
    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.daemon = True

    def run(self):
        while True:
            key, command = self.task_queue.get()
            if key is None:
                # Received poison pill, no more tasks to run
                self.task_queue.task_done()
                break
            self.log.info("%s running %s", self.__class__.__name__, command)
            command = "exec bash -c '{0}'".format(command)
            try:
                subprocess.check_call(command, shell=True)
                state = State.SUCCESS
            except subprocess.CalledProcessError as e:
                state = State.FAILED
                self.log.error("Failed to execute task %s.", str(e))
                # TODO: Why is this commented out?
                # raise e
            self.result_queue.put((key, state))
            self.task_queue.task_done()
            time.sleep(1)


class LocalExecutor(BaseExecutor):
    """
    LocalExecutor executes tasks locally in parallel. It uses the
    multiprocessing Python library and queues to parallelize the execution
    of tasks.
    """

    def start(self):
        self.queue = multiprocessing.JoinableQueue()
        self.result_queue = multiprocessing.Queue()
        self.workers = [
            LocalWorker(self.queue, self.result_queue)
            for _ in range(self.parallelism)
        ]

        for w in self.workers:
            w.start()

    def execute_async(self, key, command, queue=None):
        self.queue.put((key, command))

    def sync(self):
        while not self.result_queue.empty():
            results = self.result_queue.get()
            self.change_state(*results)

    def end(self):
        # Sending poison pill to all worker
        for _ in self.workers:
            self.queue.put((None, None))

        # Wait for commands to finish
        self.queue.join()
        self.sync()
