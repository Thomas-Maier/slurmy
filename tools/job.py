
import subprocess as sp
import os
import pickle
import logging
from .defs import Status

log = logging.getLogger('slurmy')


class JobConfig:
  def __init__(self, backend, path, success_func = None, max_retries = 0, tags = None, parent_tags = None, is_local = False, output = None):
    self.backend = backend
    self.name = self.backend.name
    self.path = path
    self.tags = set()
    if tags is not None: self.add_tags(tags)
    self.parent_tags = set()
    if parent_tags is not None: self.add_tags(parent_tags, True)
    self.success_func = success_func
    self.is_local = is_local
    self.max_retries = max_retries
    self.output = output
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
    print_string.rstrip('\n')

    return print_string

  def _reset(self):
    log.debug('({}) Reset job'.format(self.config.name))
    self.config.status = Status.Configured
    self.config.job_id = None
    self._local_process = None
    if os.path.isfile(self.config.backend.log): os.remove(self.config.backend.log)
    self.update_snapshot()

  def _write_log(self):
    log.debug('({}) Write log file'.format(self.config.name))
    with open(self.config.backend.log, 'w') as out_file:
      out_file.write(self._local_process.stdout.read())

  def wait(self):
    if self._local_process is None:
      log.warning('({}) No local process present to wait for...'.format(self.config.name))
      return
    self._local_process.wait()

  def update_snapshot(self):
    ## If no snapshot file is defined, do nothing
    if not self.config.path: return
    log.debug('({}) Update snapshot'.format(self.config.name))
    ## Check status again
    self.get_status()
    with open(self.config.path, 'wb') as out_file:
      pickle.dump(self.config, out_file)

  def set_local(self, is_local = True):
    if self.config.status != Status.Configured:
      log.warning('({}) Not in Configured state, cannot set to local'.format(self.config.name))
      raise Exception
    self.config.is_local = is_local

  def is_local(self):
    return self.config.is_local

  def add_tag(self, tag, is_parent = False):
    self.config.add_tag(tag, is_parent)
    
  def add_tags(self, tags, is_parent = False):
    self.config.add_tags(tags, is_parent)

  def submit(self):
    if self.config.status != Status.Configured:
      log.warning('({}) Not in Configured state, cannot submit'.format(self.config.name))
      raise Exception
    if self.config.is_local:
      command = self._get_local_command()
      ## preexec_fn option tells child process to ignore signal sent to main app (for KeyboardInterrupt ignore)
      ## apparently more saver options available with python 3.2+, see "start_new_session = True"
      log.debug('({}) Submit local process with command {}'.format(self.config.name, command))
      # self._local_process = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT, preexec_fn = os.setpgrp)
      self._local_process = sp.Popen(command, stdout = sp.PIPE, stderr = sp.STDOUT, start_new_session = True, universal_newlines = True)
    else:
      self.config.job_id = self.config.backend.submit()
    self.config.status = Status.Running

  def cancel(self, clear_retry = False):
    ## Do nothing if job is already in failed state
    if self.config.status == Status.Failed: return
    log.debug('({}) Cancel job'.format(self.config.name))
    ## Stop job if it's in running state
    if self.config.status == Status.Running:
      if self.config.is_local:
        self._local_process.terminate()
      else:
        self.config.backend.cancel()
    self.config.status = Status.Cancelled
    if clear_retry: self.config.max_retries = 0

  ## TODO: try to encapsulate any retry logic inside the job config and set it here
  def retry(self, force = False, submit = True):
    if not self.do_retry(): return
    log.debug('({}) Retry job'.format(self.config.name))
    if self.config.status == Status.Running:
      if enforce:
        self.cancel()
      else:
        print ("Job is still running, use force=True to force re-submit")
        return
    self._reset()
    self.config.n_retries += 1
    if submit: self.submit()

  def do_retry(self):
    return (self.config.max_retries > 0 and (self.config.n_retries < self.config.max_retries))

  def get_status(self):
    if self.config.status == Status.Running:
      if self.config.is_local:
        self._get_local_status()
      else:
        self.config.status = self.config.backend.status()
    if self.config.status == Status.Finished:
      if self._is_success():
        self.config.status = Status.Success
      else:
        self.config.status = Status.Failed
        
    return self.config.status

  def _get_local_status(self):
    self.config.exitcode = self._local_process.poll()
    if self.config.exitcode is None:
      self.config.status = Status.Running
    else:
      self.config.status = Status.Finished
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

  def get_tags(self):
    return self.config.tags

  def get_parent_tags(self):
    return self.config.parent_tags

  def get_name(self):
    return self.config.name

  def log(self):
    os.system('less {}'.format(self.config.backend.log))

  def script(self):
    os.system('less {}'.format(self.config.backend.run_script))

  def _get_local_command(self):
    command = ['/bin/bash']
    command.append(self.config.backend.run_script)
    if self.config.backend.run_args: command += self.config.backend.run_args

    return command
