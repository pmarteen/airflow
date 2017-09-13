# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 Spotify AB
# Ported to Airflow by Bolke de Bruin
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

import getpass
import os

import paramiko

from contextlib import contextmanager

from airflow.hooks.base_hook import BaseHook
from airflow.utils.log.LoggingMixin import LoggingMixin


class SSHHook(BaseHook, LoggingMixin):
    """
    Light-weight remote execution library and utilities.

    Using this hook (which is just a convenience wrapper for subprocess),
    is created to let you stream data from a remotely stored file.

    As a bonus, :class:`SSHHook` also provides a really cool feature that let's you
    set up ssh tunnels super easily using a python context manager (there is an example
    in the integration part of unittests).

    :param key_file: Typically the SSHHook uses the keys that are used by the user
        airflow is running under. This sets the behavior to use another file instead.
    :type key_file: str
    :param connect_timeout: sets the connection timeout for this connection.
    :type connect_timeout: int
    :param no_host_key_check: whether to check to host key. If True host keys will not
        be checked, but are also not stored in the current users's known_hosts file.
    :type no_host_key_check: bool
    :param tty: allocate a tty.
    :type tty: bool
    :param sshpass: Use to non-interactively perform password authentication by using
        sshpass.
    :type sshpass: bool
    """
    def __init__(self, conn_id='ssh_default'):
        conn = self.get_connection(conn_id)
        self.key_file = conn.extra_dejson.get('key_file', None)
        self.connect_timeout = conn.extra_dejson.get('connect_timeout', None)
        self.tcp_keepalive = conn.extra_dejson.get('tcp_keepalive', False)
        self.server_alive_interval = conn.extra_dejson.get('server_alive_interval', 60)
        self.no_host_key_check = conn.extra_dejson.get('no_host_key_check', False)
        self.tty = conn.extra_dejson.get('tty', False)
        self.sshpass = conn.extra_dejson.get('sshpass', False)
        self.conn = conn

    def get_conn(self):
        if not self.client:
            self.logger.debug('Creating SSH client for conn_id: %s', self.ssh_conn_id)
            if self.ssh_conn_id is not None:
                conn = self.get_connection(self.ssh_conn_id)
                if self.username is None:
                    self.username = conn.login
                if self.password is None:
                    self.password = conn.password
                if self.remote_host is None:
                    self.remote_host = conn.host
                if conn.extra is not None:
                    extra_options = conn.extra_dejson
                    self.key_file = extra_options.get("key_file")

                    if "timeout" in extra_options:
                        self.timeout = int(extra_options["timeout"], 10)

                    if "compress" in extra_options \
                            and extra_options["compress"].lower() == 'false':
                        self.compress = False
                    if "no_host_key_check" in extra_options \
                            and extra_options["no_host_key_check"].lower() == 'false':
                        self.no_host_key_check = False

            if not self.remote_host:
                raise AirflowException("Missing required param: remote_host")

            # Auto detecting username values from system
            if not self.username:
                self.logger.debug(
                    "username to ssh to host: %s is not specified for connection id"
                    " %s. Using system's default provided by getpass.getuser()",
                    self.remote_host, self.ssh_conn_id
                )
                self.username = getpass.getuser()

            host_proxy = None
            user_ssh_config_filename = os.path.expanduser('~/.ssh/config')
            if os.path.isfile(user_ssh_config_filename):
                ssh_conf = paramiko.SSHConfig()
                ssh_conf.parse(open(user_ssh_config_filename))
                host_info = ssh_conf.lookup(self.remote_host)
                if host_info and host_info.get('proxycommand'):
                    host_proxy = paramiko.ProxyCommand(host_info.get('proxycommand'))

                if not (self.password or self.key_file):
                    if host_info and host_info.get('identityfile'):
                        self.key_file = host_info.get('identityfile')[0]

            try:
                client = paramiko.SSHClient()
                client.load_system_host_keys()
                if self.no_host_key_check:
                    # Default is RejectPolicy
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                if self.password and self.password.strip():
                    client.connect(hostname=self.remote_host,
                                   username=self.username,
                                   password=self.password,
                                   timeout=self.timeout,
                                   compress=self.compress,
                                   sock=host_proxy)
                else:
                    client.connect(hostname=self.remote_host,
                                   username=self.username,
                                   key_filename=self.key_file,
                                   timeout=self.timeout,
                                   compress=self.compress,
                                   sock=host_proxy)

                self.client = client
            except paramiko.AuthenticationException as auth_error:
                self.logger.error(
                    "Auth failed while connecting to host: %s, error: %s",
                    self.remote_host, auth_error
                )
            except paramiko.SSHException as ssh_error:
                self.logger.error(
                    "Failed connecting to host: %s, error: %s",
                    self.remote_host, ssh_error
                )
            except Exception as error:
                self.logger.error(
                    "Error connecting to host: %s, error: %s",
                    self.remote_host, error
                )
        return self.client

    @contextmanager
    def tunnel(self, local_port, remote_port=None, remote_host="localhost"):
        """
        Creates a tunnel between two hosts. Like ssh -L <LOCAL_PORT>:host:<REMOTE_PORT>.
        Remember to close() the returned "tunnel" object in order to clean up
        after yourself when you are done with the tunnel.

        :param local_port:
        :type local_port: int
        :param remote_port:
        :type remote_port: int
        :param remote_host:
        :type remote_host: str
        :return:
        """
        tunnel_host = "{0}:{1}:{2}".format(local_port, remote_host, remote_port)
        proc = self.Popen(["-L", tunnel_host, "echo -n ready && cat"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        ssh_cmd = ["ssh", "{0}@{1}".format(self.username, self.remote_host),
                   "-o", "ControlMaster=no",
                   "-o", "UserKnownHostsFile=/dev/null",
                   "-o", "StrictHostKeyChecking=no"]

        ssh_tunnel_cmd = ["-L", tunnel_host,
                          "echo -n ready && cat"
                          ]

        ssh_cmd += ssh_tunnel_cmd
        self.logger.debug("Creating tunnel with cmd: %s", ssh_cmd)

        proc = subprocess.Popen(ssh_cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        ready = proc.stdout.read(5)
        assert ready == b"ready", "Did not get 'ready' from remote"
        yield
        proc.communicate()
        assert proc.returncode == 0, "Tunnel process did unclean exit (returncode {}".format(proc.returncode)

