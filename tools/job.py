
import subprocess as sp
import os
import pickle
import logging
from .defs import Status
from .utils import set_update_properties
from .updater import UpdateSet

log = logging.getLogger('slurmy')


class JobConfig:
    """@SLURMY
    Config class for the Job class. Stores all necessary information to load the Job at a later time. All properties are assigned with a custom getter function, which keeps track of updates to the respective property (tracked with the "update" variable).

    Arguments:

    * `backend` Backend instance used for the job setup.
    * `path` Path of the job's snapshot file.
    * `success_func` Success function used for the job setup.
    * `finished_func` Finished function used for the job setup.
    * `post_func` Post execution function used for the job setup.
    * `max_retries` Maximum number of retries that are attempted when job is failing.
    * `tags` List of tags attached to the job.
    * `parent_tags` List of parent tags attached to the job.
    * `is_local` Switch to define job as local.
    * `output` Output file of the job.
    """
    
    ## Properties for which custom getter/setter will be defined (without prepending "_") which incorporate the update tagging
    _properties = ['_backend', '_name', '_path', '_tags', '_parent_tags', '_success_func', '_finished_func', '_post_func',
                   '_is_local', '_max_retries', '_output', '_status', '_job_id', '_n_retries', '_exitcode']
    
    def __init__(self, backend, path, success_func = None, finished_func = None, post_func = None, max_retries = 0, tags = None, parent_tags = None, is_local = False, output = None):
        ## Static variables
        self._backend = backend
        self._name = self.backend.name
        self._path = path
        self._tags = UpdateSet(self)
        if tags is not None: self.add_tags(tags)
        self._parent_tags = UpdateSet(self)
        if parent_tags is not None: self.add_tags(parent_tags, True)
        self._success_func = success_func
        self._finished_func = finished_func
        self._post_func = post_func
        self._is_local = is_local
        self._max_retries = max_retries
        self._output = output
        ## Dynamic variables
        self._status = Status.CONFIGURED
        self._job_id = None
        self._n_retries = 0
        self._exitcode = None

    def add_tag(self, tag, is_parent = False):
        if is_parent:
            self.parent_tags.add(tag)
        else:
            self.tags.add(tag)

    def add_tags(self, tags, is_parent = False):
        if isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set):
            for tag in tags:
                self.add_tag(tag, is_parent)
        else:
            self.add_tag(tags, is_parent)
## Set properties to incorporate update tagging
set_update_properties(JobConfig)


class Job:
    """@SLURMY
    Job class that holds the job configuration and status information. Internally stores most information in the JobConfig class, which is stored on disk as a snapshot of the Job. Jobs are not meant to be set up directly but rather via JobHandler.add_job().

    Arguments:

    * `config` The JobConfig instance that defines the initial job setup.
    """
    
    def __init__(self, config):
        self.config = config
        ## Variables that are not picklable
        self._local_process = None

    def __repr__(self):
        print_string = 'Job "{}"\n'.format(self.config.name)
        print_string += 'Local: {}\n'.format(self.is_local())
        print_string += 'Backend: {}\n'.format(self.config.backend.bid)
        print_string += 'Script: {}\n'.format(self.config.backend.run_script)
        if self.config.backend.run_args: print_string += 'Args: {}\n'.format(self.config.backend.run_args)
        print_string += 'Status: {}\n'.format(self.config.status.name)
        if self.config.tags: print_string += 'Tags: {}\n'.format(self.config.tags)
        if self.config.parent_tags: print_string += 'Parent tags: {}\n'.format(self.config.parent_tags)
        if self.config.output: print_string += 'Output: {}'.format(self.config.output)

        return print_string

    def reset(self):
        log.debug('({}) Reset job'.format(self.config.name))
        self.config.status = Status.CONFIGURED
        self.config.job_id = None
        self._local_process = None
        if os.path.isfile(self.config.backend.log): os.remove(self.config.backend.log)
        self.update_snapshot()

    def _write_log(self):
        log.debug('({}) Write log file'.format(self.config.name))
        with open(self.config.backend.log, 'w') as out_file:
            out_file.write(self._local_process.stdout.read())

    def wait(self):
        """@SLURMY
        """
        if self._local_process is None:
            log.warning('({}) No local process present to wait for...'.format(self.config.name))
            return
        self._local_process.wait()

    def update_snapshot(self):
        """@SLURMY
        """
        ## If no snapshot file is defined, do nothing
        if not self.config.path: return
        ## If config is not tagged for an update, do nothing
        if not self.config.update:
            log.debug('({}) No changes made, skip snapshot update'.format(self.config.name))
            return
        log.debug('({}) Update snapshot'.format(self.config.name))
        ## Check status again
        self.get_status()
        with open(self.config.path, 'wb') as out_file:
            pickle.dump(self.config, out_file)
        ## Reset update flag
        self.config.update = False

    def set_local(self, is_local = True):
        """@SLURMY
        """
        if self.config.status != Status.CONFIGURED:
            log.warning('({}) Not in Configured state, cannot set to local'.format(self.config.name))
            raise Exception
        self.config.is_local = is_local

    def is_local(self):
        """@SLURMY
        """
        return self.config.is_local

    def add_tag(self, tag, is_parent = False):
        """@SLURMY
        Arguments:

        * `tag` Tag to add to the job.
        * `is_parent` Switch to mark tag as parent.
        """
        self.config.add_tag(tag, is_parent)

    def add_tags(self, tags, is_parent = False):
        """@SLURMY
        Arguments:

        * `tags` List of tags to add to the job.
        * `is_parent` Switch to mark tags as parent.
        """
        self.config.add_tags(tags, is_parent)

    def submit(self):
        """@SLURMY
        """
        if self.config.status != Status.CONFIGURED:
            log.warning('({}) Not in Configured state, cannot submit'.format(self.config.name))
            raise Exception
        if self.config.is_local:
            command = self._get_local_command()
            log.debug('({}) Submit local process with command {}'.format(self.config.name, command))
            self._local_process = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT, start_new_session = True, universal_newlines = True)
        else:
            self.config.job_id = self.config.backend.submit()
        self.config.status = Status.RUNNING

        return self.config.status

    def cancel(self, clear_retry = False):
        """@SLURMY
        Arguments:

        * `clear_retry` Switch to deactivate automatic retry mechanism
        """
        ## Do nothing if job is already in failed state
        if self.config.status == Status.FAILURE: return
        log.debug('({}) Cancel job'.format(self.config.name))
        ## Stop job if it's in running state
        if self.config.status == Status.RUNNING:
            if self.config.is_local:
                self._local_process.terminate()
            else:
                self.config.backend.cancel()
        self.config.status = Status.CANCELLED
        if clear_retry: self.config.max_retries = 0

        return self.config.status

    ## TODO: need some quality of life functions and make this one only internal --> rerun, rerun_local
    def _retry(self, force = False, submit = True, ignore_max_retries = False, local = False):
        """@SLURMY
        Arguments:

        * `force` Switch to force a running job to resubmit.
        * `submit` Switch to directly submit the job again.
        * `ignore_max_retries` Switch to ignore maximum number of retries.
        """
        if not ignore_max_retries and not self._do_retry(): return
        log.debug('({}) Retry job'.format(self.config.name))
        if self.config.status == Status.RUNNING:
            if force:
                self.cancel()
            else:
                print ("Job is still running, use force=True to force re-submit")
                return
        self.reset()
        self.set_local(local)
        self.config.n_retries += 1
        if submit: self.submit()

        return self.config.status

    def _do_retry(self):
        return (self.config.max_retries > 0 and (self.config.n_retries < self.config.max_retries))

    def rerun(self, local = False):
        """@SLURMY
        Resets the job and submits it again.

        Arguments:

        * `local` Switch to submit as a local job.
        """
        self._retry(ignore_max_retries = True, local = local)

    def rerun_local(self):
        """@SLURMY
        Resets the job and submits it again.
        """
        self._retry(ignore_max_retries = True)

    def get_status(self, skip_eval = False, force_success_check = False):
        """@SLURMY
        Arguments:

        * `skip_eval` Switch to skip the status evaluation and just return the stored value.
        * `force_success_check` Switch to enforce the success check, even if the job is already in a post-finished state.
        """
        ## Just return current status and skip status evaluation
        if skip_eval:
            return self.config.status
        ## Evaluate if job is finished
        if self.config.status == Status.RUNNING:
            if self.config.is_local:
                self._get_local_status()
            else:
                if self.config.finished_func is not None:
                    if self.config.finished_func(self.config):
                        self.config.status = Status.FINISHED
                    else:
                        self.config.status = Status.RUNNING
                else:
                    self.config.status = self.config.backend.status()
        ## Evaluate if job was successful
        if self.config.status == Status.FINISHED or force_success_check:
            if self._is_success():
                self.config.status = Status.SUCCESS
            else:
                self.config.status = Status.FAILURE
            ## Finish the job, TODO: maybe let the jobhandler trigger this instead?
            self._finish()

        return self.config.status

    def _get_local_status(self):
        self.config.exitcode = self._local_process.poll()
        if self.config.exitcode is None:
            self.config.status = Status.RUNNING
        else:
            self.config.status = Status.FINISHED
            self._write_log()

    def _is_success(self):
        success = False
        if self.config.success_func is None:
            if self.config.is_local:
                success = (self.config.exitcode == 0)
            else:
                self.config.exitcode = self.config.backend.exitcode()
                success = (self.config.exitcode == '0:0')
        else:
            success = self.config.success_func(self.config)

        return success

    def _finish(self):
        if self.config.post_func is not None:
            self.config.post_func(self.config)

    @property
    def tags(self):
        """@SLURMY
        Return the list of tags associated to this job.
        """
        return self.config.tags

    @property
    def parent_tags(self):
        """@SLURMY
        Return the list of parent tags associated to this job.
        """
        return self.config.parent_tags

    @property
    def name(self):
        """@SLURMY
        Return the name of the job.
        """
        return self.config.name

    @property
    def log(self):
        """@SLURMY
        Open the job log file with less.
        """
        os.system('less -R {}'.format(self.config.backend.log))

        return self.config.backend.log

    @property
    def script(self):
        """@SLURMY
        Open the job script file with less.
        """
        os.system('less -R {}'.format(self.config.backend.run_script))

        return self.config.backend.run_script

    def _get_local_command(self):
        command = ['/bin/bash']
        command.append(self.config.backend.run_script)
        if self.config.backend.run_args: command += self.config.backend.run_args

        return command
