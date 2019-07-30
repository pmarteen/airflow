# Updating Airflow

This file documents any backwards-incompatible changes in Airflow and
assists users migrating to a new version.

## Airflow Master

### Changes to S3Hook

Note: The order of arguments has changed for `check_for_prefix`. 
The `bucket_name` is now optional. It falls back to the `connection schema` attribute.

### `pool` config option in Celery section to support different Celery pool implementation

The new `pool` config option allows users to choose different pool
implementation. Default value is "prefork", while choices include "prefork" (default),
"eventlet", "gevent" or "solo". This may help users achieve better concurrency performance
in different scenarios.

For more details about Celery pool implementation, please refer to:
- https://docs.celeryproject.org/en/latest/userguide/workers.html#concurrency
- https://docs.celeryproject.org/en/latest/userguide/concurrency/eventlet.html

### Removal of `non_pooled_task_slot_count` and `non_pooled_backfill_task_slot_count`

`non_pooled_task_slot_count` and `non_pooled_backfill_task_slot_count`
are removed in favor of a real pool, e.g. `default_pool`.

By default tasks are running in `default_pool`.
`default_pool` is initialized with 128 slots and user can change the
number of slots through UI/CLI. `default_pool` cannot be removed.

### Changes to Google Transfer Operator
To obtain pylint compatibility the `filter ` argument in `GcpTransferServiceOperationsListOperator` 
has been renamed to `request_filter`.

### Changes in  Google Cloud Transfer Hook
 To obtain pylint compatibility the `filter` argument in `GCPTransferServiceHook.list_transfer_job` and 
 `GCPTransferServiceHook.list_transfer_operations` has been renamed to `request_filter`.

### Changes in writing Logs to Elasticsearch

The `elasticsearch_` prefix has been removed from all config items under the `[elasticsearch]` section. For example `elasticsearch_host` is now just `host`.

### Changes to the Google Cloud Storage Hook

Updating to `google-cloud-storage >= 1.16` changes the signature of the upstream `client.get_bucket()` method from `get_bucket(bucket_name: str)` to `get_bucket(bucket_or_name: Union[str, Bucket])`. This method is not directly exposed by the airflow hook, but any code accessing the connection directly (`GoogleCloudStorageHook().get_conn().get_bucket(...)` or similar) will need to be updated.

### Export MySQL timestamps as UTC

`MySqlToGoogleCloudStorageOperator` now exports TIMESTAMP columns as UTC
by default, rather than using the default timezone of the MySQL server.
This is the correct behavior for use with BigQuery, since BigQuery
assumes that TIMESTAMP columns without time zones are in UTC. To
preserve the previous behavior, set `ensure_utc` to `False.`

### CLI reorganization

The Airflow CLI has been organized so that related commands are grouped
together as subcommands. The `airflow list_dags` command is now `airflow
dags list`, `airflow pause` is `airflow dags pause`, etc. For a complete
list of updated CLI commands, see https://airflow.apache.org/cli.html.

### Removal of Mesos Executor

The Mesos Executor is removed from the code base as it was not widely used and not maintained. [Mailing List Discussion on deleting it](https://lists.apache.org/thread.html/daa9500026b820c6aaadeffd66166eae558282778091ebbc68819fb7@%3Cdev.airflow.apache.org%3E).

### Increase standard Dataproc disk sizes

It is highly recommended to have 1TB+ disk size for Dataproc to have sufficient throughput:
https://cloud.google.com/compute/docs/disks/performance

Hence, the default value for `master_disk_size` in DataprocClusterCreateOperator has beeen changes from 500GB to 1TB.

### Changes to SalesforceHook

* renamed `sign_in` function to `get_conn` 

### HTTPHook verify default value changed from False to True.

The HTTPHook is now secured by default: `verify=True`.
This can be overwriten by using the extra_options param as `{'verify': False}`.

### Changes to GoogleCloudStorageHook

* the discovery-based api (`googleapiclient.discovery`) used in `GoogleCloudStorageHook` is now replaced by the recommended client based api (`google-cloud-storage`). To know the difference between both the libraries, read https://cloud.google.com/apis/docs/client-libraries-explained. PR: [#5054](https://github.com/apache/airflow/pull/5054) 
* as a part of this replacement, the `multipart` & `num_retries` parameters for `GoogleCloudStorageHook.upload` method have been removed.
  
  The client library uses multipart upload automatically if the object/blob size is more than 8 MB - [source code](https://github.com/googleapis/google-cloud-python/blob/11c543ce7dd1d804688163bc7895cf592feb445f/storage/google/cloud/storage/blob.py#L989-L997). The client also handles retries automatically

* the `generation` parameter is removed in `GoogleCloudStorageHook.delete` and `GoogleCloudStorageHook.insert_object_acl`. 

* The following parameters have been replaced in all the methods in GCSHook:
  * `bucket` is changed to `bucket_name`
  * `object` is changed to `object_name` 
  
* The `maxResults` parameter in `GoogleCloudStorageHook.list` has been renamed to `max_results` for consistency.

### Changes to CloudantHook

* upgraded cloudant version from `>=0.5.9,<2.0` to `>=2.0`
* removed the use of the `schema` attribute in the connection
* removed `db` function since the database object can also be retrieved by calling `cloudant_session['database_name']`

For example:
```python
from airflow.contrib.hooks.cloudant_hook import CloudantHook

with CloudantHook().get_conn() as cloudant_session:
    database = cloudant_session['database_name']
```

See the [docs](https://python-cloudant.readthedocs.io/en/latest/) for more information on how to use the new cloudant version.

### Changes to DatastoreHook

* removed argument `version` from `get_conn` function and added it to the hook's `__init__` function instead and renamed it to `api_version`
* renamed the `partialKeys` argument of function `allocate_ids` to `partial_keys`

### Unify default conn_id for Google Cloud Platform

Previously not all hooks and operators related to Google Cloud Platform use
``google_cloud_default`` as a default conn_id. There is currently one default
variant. Values like ``google_cloud_storage_default``, ``bigquery_default``,
``google_cloud_datastore_default`` have been deprecated. The configuration of
existing relevant connections in the database have been preserved. To use those
deprecated GCP conn_id, you need to explicitly pass their conn_id into
operators/hooks. Otherwise, ``google_cloud_default`` will be used as GCP's conn_id
by default.

### Viewer won't have edit permissions on DAG view.

### New `dag_discovery_safe_mode` config option

If `dag_discovery_safe_mode` is enabled, only check files for DAGs if
they contain the strings "airflow" and "DAG". For backwards
compatibility, this option is enabled by default.

### Removed deprecated import mechanism

The deprecated import mechanism has been removed so the import of modules becomes more consistent and explicit.

For example: `from airflow.operators import BashOperator`
becomes `from airflow.operators.bash_operator import BashOperator`

### Changes to sensor imports

Sensors are now accessible via `airflow.sensors` and no longer via `airflow.operators.sensors`.

For example: `from airflow.operators.sensors import BaseSensorOperator`
becomes `from airflow.sensors.base_sensor_operator import BaseSensorOperator`

### Renamed "extra" requirements for cloud providers

Subpackages for specific services have been combined into one variant for
each cloud provider. The name of the subpackage for the Google Cloud Platform
has changed to follow style.

If you want to install integration for Microsoft Azure, then instead of
```
pip install 'apache-airflow[azure_blob_storage,azure_data_lake,azure_cosmos,azure_container_instances]'
```
you should execute `pip install 'apache-airflow[azure]'`

If you want to install integration for Amazon Web Services, then instead of
`pip install 'apache-airflow[s3,emr]'`, you should execute `pip install 'apache-airflow[aws]'`

If you want to install integration for Google Cloud Platform, then instead of
`pip install 'apache-airflow[gcp_api]'`, you should execute `pip install 'apache-airflow[gcp]'`.
The old way will work until the release of Airflow 2.1.

### Deprecate legacy UI in favor of FAB RBAC UI
Previously we were using two versions of UI, which were hard to maintain as we need to implement/update the same feature
in both versions. With this change we've removed the older UI in favor of Flask App Builder RBAC UI. No need to set the
RBAC UI explicitly in the configuration now as this is the only default UI.
Please note that that custom auth backends will need re-writing to target new FAB based UI.

As part of this change, a few configuration items in `[webserver]` section are removed and no longer applicable,
including `authenticate`, `filter_by_owner`, `owner_mode`, and `rbac`.


#### Remove run_duration

We should not use the `run_duration` option anymore. This used to be for restarting the scheduler from time to time, but right now the scheduler is getting more stable and therefore using this setting is considered bad and might cause an inconsistent state.

### New `dag_processor_manager_log_location` config option

The DAG parsing manager log now by default will be log into a file, where its location is
controlled by the new `dag_processor_manager_log_location` config option in core section.

### min_file_parsing_loop_time config option temporarily disabled

The scheduler.min_file_parsing_loop_time config option has been temporarily removed due to
some bugs.

### CLI Changes

The ability to manipulate users from the command line has been changed. 'airflow create_user' and 'airflow delete_user' and 'airflow list_users' has been grouped to a single command `airflow users` with optional flags `--create`, `--list` and `--delete`.

Example Usage:

To create a new user:
```bash
airflow users --create --username jondoe --lastname doe --firstname jon --email jdoe@apache.org --role Viewer --password test
```

To list users:
```bash
airflow users --list
```

To delete a user:
```bash
airflow users --delete --username jondoe
```

To add a user to a role:
```bash
airflow users --add-role --username jondoe --role Public
```

To remove a user from a role:
```bash
airflow users --remove-role --username jondoe --role Public
```

### Unification of `do_xcom_push` flag
The `do_xcom_push` flag (a switch to push the result of an operator to xcom or not) was appearing in different incarnations in different operators. It's function has been unified under a common name (`do_xcom_push`) on `BaseOperator`. This way it is also easy to globally disable pushing results to xcom.

See [AIRFLOW-3249](https://jira.apache.org/jira/browse/AIRFLOW-3249) to check if your operator was affected.

### Changes to Dataproc related Operators
The 'properties' and 'jars' properties for the Dataproc related operators (`DataprocXXXOperator`) have been renamed from 
`dataproc_xxxx_properties` and `dataproc_xxx_jars`  to `dataproc_properties`
and `dataproc_jars`respectively. 
Arguments for dataproc_properties dataproc_jars 

## Airflow 1.10.3

### RedisPy dependency updated to v3 series
If you are using the Redis Sensor or Hook you may have to update your code. See
[redis-py porting instructions] to check if your code might be affected (MSET,
MSETNX, ZADD, and ZINCRBY all were, but read the full doc).

[redis-py porting instructions]: https://github.com/andymccurdy/redis-py/tree/3.2.0#upgrading-from-redis-py-2x-to-30

### SLUGIFY_USES_TEXT_UNIDECODE or AIRFLOW_GPL_UNIDECODE no longer required

It is no longer required to set one of the environment variables to avoid
a GPL dependency. Airflow will now always use text-unidecode if unidecode
was not installed before.

### new `sync_parallelism` config option in celery section

The new `sync_parallelism` config option will control how many processes CeleryExecutor will use to
fetch celery task state in parallel. Default value is max(1, number of cores - 1)

### Rename of BashTaskRunner to StandardTaskRunner

BashTaskRunner has been renamed to StandardTaskRunner. It is the default task runner
so you might need to update your config.

`task_runner = StandardTaskRunner`

### Modification to config file discovery

If the `AIRFLOW_CONFIG` environment variable was not set and the
`~/airflow/airflow.cfg` file existed, airflow previously used
`~/airflow/airflow.cfg` instead of `$AIRFLOW_HOME/airflow.cfg`. Now airflow
will discover its config file using the `$AIRFLOW_CONFIG` and `$AIRFLOW_HOME`
environment variables rather than checking for the presence of a file.

### New `dag_discovery_safe_mode` config option

If `dag_discovery_safe_mode` is enabled, only check files for DAGs if
they contain the strings "airflow" and "DAG". For backwards
compatibility, this option is enabled by default.

### Changes in Google Cloud Platform related operators

Most GCP-related operators have now optional `PROJECT_ID` parameter. In case you do not specify it,
the project id configured in
[GCP Connection](https://airflow.apache.org/howto/manage-connections.html#connection-type-gcp) is used.
There will be an `AirflowException` thrown in case `PROJECT_ID` parameter is not specified and the
connection used has no project id defined. This change should be  backwards compatible as earlier version
of the operators had `PROJECT_ID` mandatory.

Operators involved:

  * GCP Compute Operators
    * GceInstanceStartOperator
    * GceInstanceStopOperator
    * GceSetMachineTypeOperator
  * GCP Function Operators
    * GcfFunctionDeployOperator
  * GCP Cloud SQL Operators
    * CloudSqlInstanceCreateOperator
    * CloudSqlInstancePatchOperator
    * CloudSqlInstanceDeleteOperator
    * CloudSqlInstanceDatabaseCreateOperator
    * CloudSqlInstanceDatabasePatchOperator
    * CloudSqlInstanceDatabaseDeleteOperator

Other GCP operators are unaffected.

### Changes in Google Cloud Platform related hooks

The change in GCP operators implies that GCP Hooks for those operators require now keyword parameters rather
than positional ones in all methods where `project_id` is used. The methods throw an explanatory exception
in case they are called using positional parameters.

Hooks involved:

  * GceHook
  * GcfHook
  * CloudSqlHook

Other GCP hooks are unaffected.

### Changed behaviour of using default value when accessing variables
It's now possible to use `None` as a default value with the `default_var` parameter when getting a variable, e.g.

```python
foo = Variable.get("foo", default_var=None)
if foo is None:
    handle_missing_foo()
```

(Note: there is already `Variable.setdefault()` which me be helpful in some cases.)

This changes the behaviour if you previously explicitly provided `None` as a default value. If your code expects a `KeyError` to be thrown, then don't pass the `default_var` argument.

### Removal of `airflow_home` config setting

There were previously two ways of specifying the Airflow "home" directory
(`~/airflow` by default): the `AIRFLOW_HOME` environment variable, and the
`airflow_home` config setting in the `[core]` section.

If they had two different values different parts of the code base would end up
with different values. The config setting has been deprecated, and you should
remove the value from the config file and set `AIRFLOW_HOME` environment
variable if you need to use a non default value for this.

(Since this setting is used to calculate what config file to load, it is not
possible to keep just the config option)

### Change of two methods signatures in `GCPTransferServiceHook`

The signature of the `create_transfer_job` method in `GCPTransferServiceHook`
class has changed. The change does not change the behavior of the method.

Old signature:
```python
def create_transfer_job(self, description, schedule, transfer_spec, project_id=None):
```
New signature:
```python
def create_transfer_job(self, body):
```

It is necessary to rewrite calls to method. The new call looks like this:
```python
body = {
  'status': 'ENABLED',
  'projectId': project_id,
  'description': description,
  'transferSpec': transfer_spec,
  'schedule': schedule,
}
gct_hook.create_transfer_job(body)
```
The change results from the unification of all hooks and adjust to
[the official recommendations](https://lists.apache.org/thread.html/e8534d82be611ae7bcb21ba371546a4278aad117d5e50361fd8f14fe@%3Cdev.airflow.apache.org%3E)
for the Google Cloud Platform.

The signature of `wait_for_transfer_job` method in `GCPTransferServiceHook` has changed.

Old signature:
```python
def wait_for_transfer_job(self, job):
```
New signature:
```python
def wait_for_transfer_job(self, job, expected_statuses=(GcpTransferOperationStatus.SUCCESS, )):
```

The behavior of `wait_for_transfer_job` has changed:

Old behavior:

`wait_for_transfer_job` would wait for the SUCCESS status in specified jobs operations.

New behavior:

You can now specify an array of expected statuses. `wait_for_transfer_job` now waits for any of them.

The default value of `expected_statuses` is SUCCESS so that change is backwards compatible.

### Moved two classes to different modules

The class `GoogleCloudStorageToGoogleCloudStorageTransferOperator` has been moved from
`airflow.contrib.operators.gcs_to_gcs_transfer_operator` to `airflow.contrib.operators.gcp_transfer_operator`

the class `S3ToGoogleCloudStorageTransferOperator` has been moved from
`airflow.contrib.operators.s3_to_gcs_transfer_operator` to `airflow.contrib.operators.gcp_transfer_operator`

The change was made to keep all the operators related to GCS Transfer Services in one file.

The previous imports will continue to work until Airflow 2.0

### Fixed typo in --driver-class-path in SparkSubmitHook

The `driver_classapth` argument  to SparkSubmit Hook and Operator was
generating `--driver-classpath` on the spark command line, but this isn't a
valid option to spark.

The argument has been renamed to `driver_class_path`  and  the option it
generates has been fixed.


## Airflow 1.10.2

### DAG level Access Control for new RBAC UI

Extend and enhance new Airflow RBAC UI to support DAG level ACL. Each dag now has two permissions(one for write, one for read) associated('can_dag_edit', 'can_dag_read').
The admin will create new role, associate the dag permission with the target dag and assign that role to users. That user can only access / view the certain dags on the UI
that he has permissions on. If a new role wants to access all the dags, the admin could associate dag permissions on an artificial view(``all_dags``) with that role.

We also provide a new cli command(``sync_perm``) to allow admin to auto sync permissions.

### Modification to `ts_nodash` macro
`ts_nodash` previously contained TimeZone information along with execution date. For Example: `20150101T000000+0000`. This is not user-friendly for file or folder names which was a popular use case for `ts_nodash`. Hence this behavior has been changed and using `ts_nodash` will no longer contain TimeZone information, restoring the pre-1.10 behavior of this macro. And a new macro `ts_nodash_with_tz` has been added which can be used to get a string with execution date and timezone info without dashes.

## Master

### SSH Hook updates, along with new SSH Operator & SFTP Operator

SSH Hook now uses Paramiko library to create ssh client connection, instead of sub-process based ssh command execution previously (<1.9.0), so this is backward incompatible.
  - update SSHHook constructor
  - use SSHOperator class in place of SSHExecuteOperator which is removed now. Refer test_ssh_operator.py for usage info.
  - SFTPOperator is added to perform secure file transfer from serverA to serverB. Refer test_sftp_operator.py.py for usage info.
  - No updates are required if you are using ftpHook, it will continue work as is.

### S3Hook switched to use Boto3

The airflow.hooks.S3_hook.S3Hook has been switched to use boto3 instead of the older boto (a.k.a. boto2). This result in a few backwards incompatible changes to the following classes: S3Hook:
  - the constructors no longer accepts `s3_conn_id`. It is now called `aws_conn_id`.
  - the default conneciton is now "aws_default" instead of "s3_default"
  - the return type of objects returned by `get_bucket` is now boto3.s3.Bucket
  - the return type of `get_key`, and `get_wildcard_key` is now an boto3.S3.Object.

If you are using any of these in your DAGs and specify a connection ID you will need to update the parameter name for the connection to "aws_conn_id": S3ToHiveTransfer, S3PrefixSensor, S3KeySensor, RedshiftToS3Transfer.

### Logging update
Airflow's logging has been rewritten to uses Python’s builtin `logging` module to perform system logging. By extending classes with the existing `LoggingMixin`, all the logging will go through a central logger. The main benefit that this brings to us is the easy configuration of the logging through `default_airflow_logging.py` and the ability to use different handlers for logging.

Logs now are stored in the log folder as `{dag_id}/{task_id}/{execution_date}/{try_number}.log`.

### New Features

#### Dask Executor

A new DaskExecutor allows Airflow tasks to be run in Dask Distributed clusters.

### Deprecated Features
These features are marked for deprecation. They may still work (and raise a `DeprecationWarning`), but are no longer
supported and will be removed entirely in Airflow 2.0

- `post_execute()` hooks now take two arguments, `context` and `result`
  (AIRFLOW-886)

  Previously, post_execute() only took one argument, `context`.

## Airflow 1.8.1

The Airflow package name was changed from `airflow` to `apache-airflow` during this release. You must uninstall your
previously installed version of Airflow before installing 1.8.1.

## Airflow 1.8

### Database
The database schema needs to be upgraded. Make sure to shutdown Airflow and make a backup of your database. To
upgrade the schema issue `airflow upgradedb`.

### Upgrade systemd unit files
Systemd unit files have been updated. If you use systemd please make sure to update these.

> Please note that the webserver does not detach properly, this will be fixed in a future version.

### Tasks not starting although dependencies are met due to stricter pool checking
Airflow 1.7.1 has issues with being able to over subscribe to a pool, ie. more slots could be used than were
available. This is fixed in Airflow 1.8.0, but due to past issue jobs may fail to start although their
dependencies are met after an upgrade. To workaround either temporarily increase the amount of slots above
the the amount of queued tasks or use a new pool.

### Less forgiving scheduler on dynamic start_date
Using a dynamic start_date (e.g. `start_date = datetime.now()`) is not considered a best practice. The 1.8.0 scheduler
is less forgiving in this area. If you encounter DAGs not being scheduled you can try using a fixed start_date and
renaming your dag. The last step is required to make sure you start with a clean slate, otherwise the old schedule can
interfere.

### New and updated scheduler options
Please read through these options, defaults have changed since 1.7.1.

#### child_process_log_directory
In order the increase the robustness of the scheduler, DAGS our now processed in their own process. Therefore each 
DAG has its own log file for the scheduler. These are placed in `child_process_log_directory` which defaults to 
`<AIRFLOW_HOME>/scheduler/latest`. You will need to make sure these log files are removed.

> DAG logs or processor logs ignore and command line settings for log file locations.

#### run_duration
Previously the command line option `num_runs` was used to let the scheduler terminate after a certain amount of
loops. This is now time bound and defaults to `-1`, which means run continuously. See also num_runs.

#### num_runs
Previously `num_runs` was used to let the scheduler terminate after a certain amount of loops. Now num_runs specifies 
the number of times to try to schedule each DAG file within `run_duration` time. Defaults to `-1`, which means try
indefinitely. This is only available on the command line.

#### min_file_process_interval
After how much time should an updated DAG be picked up from the filesystem.

#### dag_dir_list_interval
How often the scheduler should relist the contents of the DAG directory. If you experience that while developing your
dags are not being picked up, have a look at this number and decrease it when necessary.

#### catchup_by_default
By default the scheduler will fill any missing interval DAG Runs between the last execution date and the current date.
This setting changes that behavior to only execute the latest interval. This can also be specified per DAG as 
`catchup = False / True`. Command line backfills will still work.

### Faulty Dags do not show an error in the Web UI

Due to changes in the way Airflow processes DAGs the Web UI does not show an error when processing a faulty DAG. To
find processing errors go the `child_process_log_directory` which defaults to `<AIRFLOW_HOME>/scheduler/latest`.

### New DAGs are paused by default

Previously, new DAGs would be scheduled immediately. To retain the old behavior, add this to airflow.cfg:

```
[core]
dags_are_paused_at_creation = False
```

### Airflow Context variable are passed to Hive config if conf is specified

If you specify a hive conf to the run_cli command of the HiveHook, Airflow add some
convenience variables to the config. In case your run a sceure Hadoop setup it might be
required to whitelist these variables by adding the following to your configuration:

```
<property> 
     <name>hive.security.authorization.sqlstd.confwhitelist.append</name>
     <value>airflow\.ctx\..*</value>
</property>
```
### Google Cloud Operator and Hook alignment

All Google Cloud Operators and Hooks are aligned and use the same client library. Now you have a single connection 
type for all kinds of Google Cloud Operators.

If you experience problems connecting with your operator make sure you set the connection type "Google Cloud Platform".

Also the old P12 key file type is not supported anymore and only the new JSON key files are supported as a service 
account.

### Deprecated Features
These features are marked for deprecation. They may still work (and raise a `DeprecationWarning`), but are no longer 
supported and will be removed entirely in Airflow 2.0

- Hooks and operators must be imported from their respective submodules

  `airflow.operators.PigOperator` is no longer supported; `from airflow.operators.pig_operator import PigOperator` is. 
  (AIRFLOW-31, AIRFLOW-200)

- Operators no longer accept arbitrary arguments

  Previously, `Operator.__init__()` accepted any arguments (either positional `*args` or keyword `**kwargs`) without 
  complaint. Now, invalid arguments will be rejected. (https://github.com/apache/incubator-airflow/pull/1285)

### Known Issues
There is a report that the default of "-1" for num_runs creates an issue where errors are reported while parsing tasks.
It was not confirmed, but a workaround was found by changing the default back to `None`.

To do this edit `cli.py`, find the following:

```
        'num_runs': Arg(
            ("-n", "--num_runs"),
            default=-1, type=int,
            help="Set the number of runs to execute before exiting"),
```

and change `default=-1` to `default=None`. Please report on the mailing list if you have this issue.

## Airflow 1.7.1.2

### Changes to Configuration

#### Email configuration change

To continue using the default smtp email backend, change the email_backend line in your config file from:

```
[email]
email_backend = airflow.utils.send_email_smtp
```
to:
```
[email]
email_backend = airflow.utils.email.send_email_smtp
```

#### S3 configuration change

To continue using S3 logging, update your config file so:

```
s3_log_folder = s3://my-airflow-log-bucket/logs
```
becomes:
```
remote_base_log_folder = s3://my-airflow-log-bucket/logs
remote_log_conn_id = <your desired s3 connection>
```
