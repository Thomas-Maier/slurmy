
import multiprocessing as mp
import os
from slurmyDef import Status
from slurmUtils import slurm_submit, slurm_cancel, slurm_status, slurm_exitcode


class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self, name, run_script, log_file, partition, success_func = None, tags = None, parent_tags = None, is_local = False):
    self._name = name
    self._run_script = run_script
    self._log_file = log_file
    self._partition = partition
    self._status = Status.Configured
    self._job_id = None
    self._tags = set()
    if tags is not None: self.add_tags(tags)
    self._parent_tags = set()
    if parent_tags is not None: self.add_tags(parent_tags, True)
    self._success_func = None
    if success_func is not None: self._success_func = success_func
    self._is_local = is_local
    self._local_process = None

  def set_local(self, is_local = True):
    if self._status != Status.Configured:
      print ('Job is not in Configured state, cannot set to local')
      raise
    self._is_local = is_local

  def is_local(self):
    return self._is_local

  def add_tag(self, tag, is_parent = False):
    if is_parent:
      self._parent_tags.add(tag)
    else:
      self._tags.add(tag)
    
  def add_tags(self, tags, is_parent = False):
    if isinstance(tags, list) or isinstance(tags, tuple):
      for tag in tags:
        self.add_tag(tag, is_parent)
    else:
      self.add_tag(tags, is_parent)

  def submit(self):
    if self._status != Status.Configured:
      print ('Job is not in Configured state, cannot submit')
      raise
    if self._is_local:
      self._local_process = mp.Process(target = Job._submit_local, args = (self._run_script, self._log_file))
      self._local_process.start()
    else:
      self._job_id = slurm_submit(self._name, self._log_file, self._partition, self._run_script)
    self._status = Status.Running

  def cancel(self):
    if self._status != Status.Running:
      print ('Job is not in running state')
      return
    if self._is_local:
      self._local_process.terminate()
    else:
      slurm_cancel(self._job_id)
    self._status = Status.Cancelled

  def get_status(self):
    if self._status == Status.Running:
      if self._is_local:
        self._status = Job._get_local_status(self._local_process)
      else:
        self._status = slurm_status(self._job_id)
    if self._status == Status.Finished:
      if self._is_success():
        self._status = Status.Success
      else:
        self._status = Status.Failed
        
    return self._status

  def _is_success(self):
    success = False
    if self._success_func is None:
      if self._is_local:
        success = (self._local_process.exitcode == 0)
      else:
        success = (slurm_exitcode(self._job_id) == '0:0')
    else:
      success = self._success_func()

    return success

  def get_tags(self):
    return self._tags

  def get_parent_tags(self):
    return self._parent_tags

  def get_name(self):
    return self._name

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
