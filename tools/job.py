
import multiprocessing as mp
import os
import pickle
from slurmyDef import Status
from slurmUtils import slurm_submit, slurm_cancel, slurm_status, slurm_exitcode


class JobConfig:
  def __init__(self, name, path, run_script, run_args, log_file, partition, success_func = None, tags = None, parent_tags = None, is_local = False, max_retries = 0):
    self.name = name
    self.path = path
    self.run_script = run_script
    self.run_args = run_args
    self.log_file = log_file
    self.partition = partition
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

  def add_tag(self, tag, is_parent = False):
    if is_parent:
      self.parent_tags.add(tag)
    else:
      self.tags.add(tag)

  def add_tags(self, tags, is_parent = False):
    if isinstance(tags, list) or isinstance(tags, tuple):
      for tag in tags:
        self.add_tag(tag, is_parent)
    else:
      self.add_tag(tags, is_parent)

class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self, config):
    self._config = config
    ## Variables that are not picklable
    self._local_process = None

  def _reset(self):
    self._config.status = Status.Configured
    self._config.job_id = None
    self._local_process = None
    if os.path.isfile(self._config.log_file): os.remove(self._config.log_file)

  def _update_snapshot(self):
    ## If no snapshot file is defined, do nothing
    if not self._config.path: return
    with open(self._config.path, 'wb') as out_file:
      pickle.dump(self._config, out_file)

  def set_local(self, is_local = True):
    if self._config.status != Status.Configured:
      print ('Job is not in Configured state, cannot set to local')
      raise
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
      raise
    if self._config.is_local:
      self._local_process = mp.Process(target = Job._submit_local, args = (self._config.run_script, self._config.log_file))
      self._local_process.start()
    else:
      self._config.job_id = slurm_submit(self._config.name, self._config.log_file, self._config.partition, self._config.run_script, run_args = self._config.run_args)
    self._config.status = Status.Running
    self._update_snapshot()

  def cancel(self, clear_retry = False):
    ## Do nothing if job is already in failed state
    if self._config.status == Status.Failed: return
    ## Stop job if it's in running state
    if self._config.status == Status.Running:
      if self._config.is_local:
        self._local_process.terminate()
      else:
        slurm_cancel(self._config.job_id)
    self._config.status = Status.Cancelled
    if clear_retry: self._config.max_retries = 0
    self._update_snapshot()

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
        self._config.status = Job._get_local_status(self._local_process)
      else:
        self._config.status = slurm_status(self._config.job_id)
    if self._config.status == Status.Finished:
      if self._is_success():
        self._config.status = Status.Success
      else:
        self._config.status = Status.Failed
        
    return self._config.status

  def _is_success(self):
    success = False
    if self._config.success_func is None:
      if self._config.is_local:
        success = (self._local_process.exitcode == 0)
      else:
        success = (slurm_exitcode(self._config.job_id) == '0:0')
    else:
      success = self._config.success_func()

    return success

  def get_tags(self):
    return self._config.tags

  def get_parent_tags(self):
    return self._config.parent_tags

  def get_name(self):
    return self._config.name

  @staticmethod
  def _submit_local(run_script, log_file):
    ## Make sure that the process finds the files, if relative paths are given
    if not run_script.startswith('/'): run_script = './'+run_script
    if not log_file.startswith('/'): log_file = './'+log_file
    r = os.system('. '+run_script+' 2>&1 > '+log_file)

    return r

  @staticmethod
  def _get_local_status(process):
    status = None
    if process.is_alive():
      status = Status.Running
    else:
      status = Status.Finished

    return status
