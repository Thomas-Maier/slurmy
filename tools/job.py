
# import multiprocessing as mp
import subprocess as sp
import os
import pickle
from slurmy.tools.defs import Status


class JobConfig:
  def __init__(self, backend, path, success_func = None, max_retries = 0, tags = None, parent_tags = None, is_local = False):
    self.backend = backend
    self.name = self.backend.name
    self.path = path
    self.tags = set()
    if tags is not None: self.add_tags(tags)
    self.parent_tags = set()
    if parent_tags is not None: self.add_tags(parent_tags, True)
    self.success_func = None
    if success_func is not None: self.success_func = success_func
    self.is_local = is_local
    self.max_retries = max_retries
    self.status = Status.Configured
    self.job_id = None
    self.n_retries = 0
    self.exitcode = None

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

class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  ## TODO: snaphot trigger should come from jobhandler? Probably better to avoid unnecessary overhead (really only need to make snapshots when python process is stopped).
  ## TODO: local_job.terminate() does not properly terminate whatever was executed in the run_script...

  def __init__(self, config):
    self._config = config
    ## Variables that are not picklable
    self._local_process = None

  def __repr__(self):
    print_string = 'Job "{}"\n'.format(self._config.name)
    print_string += 'Backend: {}\n'.format(self._config.backend.bid)
    print_string += 'Script: {}\n'.format(self._config.backend.run_script)
    if self._config.backend.run_args: print_string += 'Args: {}\n'.format(self._config.backend.run_args)
    print_string += 'Status: {}\n'.format(self._config.status.name)
    if self._config.tags: print_string += 'Tags: {}\n'.format(self._config.tags)
    if self._config.parent_tags: print_string += 'Parent tags: {}\n'.format(self._config.parent_tags)

    return print_string

  def _reset(self):
    self._config.status = Status.Configured
    self._config.job_id = None
    self._local_process = None
    if os.path.isfile(self._config.backend.log): os.remove(self._config.backend.log)
    self.update_snapshot()

  def _write_log(self):
    with open(self._config.backend.log, 'w') as out_file:
      out_file.write(self._local_process.stdout.read())

  def wait(self):
    if self._local_process is None:
      print ('No local process present to wait for...')
      return
    self._local_process.wait()

  def update_snapshot(self):
    ## If no snapshot file is defined, do nothing
    if not self._config.path: return
    ## Check status again
    self.get_status()
    with open(self._config.path, 'wb') as out_file:
      pickle.dump(self._config, out_file)

  def set_local(self, is_local = True):
    if self._config.status != Status.Configured:
      print ('Job is not in Configured state, cannot set to local')
      raise Exception
    self._config.is_local = is_local

  def is_local(self):
    return self._config.is_local

  def add_tag(self, tag, is_parent = False):
    self._config.add_tag(tag, is_parent)
    
  def add_tags(self, tags, is_parent = False):
    self._config.add_tags(tags, is_parent)

  def submit(self):
    if self._config.status != Status.Configured:
      print ('Job is not in Configured state, cannot submit')
      raise Exception
    if self._config.is_local:
      command = self._get_local_command()
      ## preexec_fn option tells child process to ignore signal sent to main app (for KeyboardInterrupt ignore)
      ## apparently more saver options available with python 3.2+, see "start_new_session = True"
      # self._local_process = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT, preexec_fn = os.setpgrp)
      self._local_process = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT, start_new_session = True, universal_newlines = True)
    else:
      self._config.job_id = self._config.backend.submit()
    self._config.status = Status.Running

  def cancel(self, clear_retry = False):
    ## Do nothing if job is already in failed state
    if self._config.status == Status.Failed: return
    ## Stop job if it's in running state
    if self._config.status == Status.Running:
      if self._config.is_local:
        self._local_process.terminate()
      else:
        self._config.backend.cancel()
    self._config.status = Status.Cancelled
    if clear_retry: self._config.max_retries = 0

  ## TODO: try to encapsulate any retry logic inside the job config and set it here
  def retry(self, force = False, submit = True):
    if not self.do_retry(): return
    if self._config.status == Status.Running:
      if enforce:
        self.cancel()
      else:
        print ("Job is still running, use force=True to force re-submit")
        return
    self._reset()
    self._config.n_retries += 1
    if submit: self.submit()

  def do_retry(self):
    return (self._config.max_retries > 0 and (self._config.n_retries < self._config.max_retries))

  def get_status(self):
    if self._config.status == Status.Running:
      if self._config.is_local:
        self._get_local_status()
      else:
        self._config.status = self._config.backend.status()
    if self._config.status == Status.Finished:
      if self._is_success():
        self._config.status = Status.Success
      else:
        self._config.status = Status.Failed
        
    return self._config.status

  def _get_local_status(self):
    self._config.exitcode = self._local_process.poll()
    if self._config.exitcode is None:
      self._config.status = Status.Running
    else:
      self._config.status = Status.Finished
      self._write_log()

  def _is_success(self):
    success = False
    if self._config.success_func is None:
      if self._config.is_local:
        success = (self._config.exitcode == 0)
      else:
        self._config.exitcode = self._config.backend.exitcode()
        success = (self._config.exitcode == '0:0')
    else:
      success = self._config.success_func(self._config)

    return success

  def get_tags(self):
    return self._config.tags

  def get_parent_tags(self):
    return self._config.parent_tags

  def get_name(self):
    return self._config.name

  def log(self):
    os.system('less {}'.format(self._config.backend.log))

  def script(self):
    os.system('less {}'.format(self._config.backend.run_script))

  def _get_local_command(self):
    command = ['/bin/bash']
    command.append(self._config.backend.run_script)
    if self._config.backend.run_args: command += self._config.backend.run_args

    return command

  @staticmethod
  def _submit_local(run_script, log_file):
    ## Make sure that the process finds the files, if relative paths are given
    if not run_script.startswith('/'): run_script = './'+run_script
    if not log_file.startswith('/'): log_file = './'+log_file
    try:
      r = -1
      r = os.system('. '+run_script+' 2>&1 > '+log_file)
      return r
    except KeyboardInterrupt:
      return -1
