
from __future__ import print_function
import os
import subprocess
import time
from enum import Enum
from sys import stdout


class Status(Enum):
  Configured = 0
  Running = 1
  Finished = 2
  Success = 3
  Failed = 4
  Cancelled = 5

## TODO: Make more stuff optional and add more options (clusters, qos)
def slurm_submit(job_name, log_name, partition, run_script):
  submit_string = subprocess.check_output(['sbatch', '-J', job_name, '-o', log_name, '-p', partition, run_script])
  job_id = int(submit_string.split(' ')[-1].rstrip('\n'))

  return job_id
  # -x exlude
  # -M clusters
  # -M lcg -p lcg_serial --qos=lcg_add

def slurm_cancel(job_id):
  cancel_string = 'scancel {}'.format(job_id)
  os.system(cancel_string)

## TODO: retrieve status via sacct (field "State")?
def slurm_status(job_id):
  status_string = subprocess.check_output(['squeue', '-j', str(job_id)])
  n_lines = status_string.count('\n')
  status = Status.Finished
  if n_lines > 1:
    status = Status.Running

  return status

def slurm_exitcode(job_id):
  sacct_string = subprocess.check_output(['sacct', '-j', str(job_id), '-P', '-o', 'ExitCode'])

  return sacct_string.split('\n')[1]


class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self, name, run_script, log_file, partition, success_func = None, tags = None, parent_tags = None):
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
    if self._status == Status.Configured:
      self._job_id = slurm_submit(self._name, self._log_file, self._partition, self._run_script)
      self._status = Status.Running

  def cancel(self):
    if self._status != Status.Running:
      print ('Job is not in running state')
    else:
      slurm_cancel(self._job_id)
      self._status = Status.Cancelled

  def get_status(self):
    if self._status == Status.Running:
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


class JobHandler:

  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs
  ## TODO: Currently not really working with jobs without any args
  ## TODO: Make default setting of stuff like partition and make optional to also define on job to job basis
  ## TODO: Local job submission (with multiprocessing or subprocess.Popen)

  def __init__(self, name = 'hans', partition = None):
    self._name = name
    self._script_folder = self._name+'/scripts/'
    self._log_folder = self._name+'/logs/'
    self._jobs = []
    self._tagged_jobs = {}
    self._job_counter = set()
    self._partition = None
    if partition: self._partition = partition
    self.reset()

  def reset(self):
    if os.path.isdir(self._script_folder): os.system('rm -r '+self._script_folder)
    os.makedirs(self._script_folder)
    if os.path.isdir(self._log_folder): os.system('rm -r '+self._log_folder)
    os.makedirs(self._log_folder)

  ## TODO: Make this a generator instead
  def get_jobs(self, tags = None):
    job_list = []
    for job in self._jobs:
      if tags is not None and not JobHandler._has_tags(job, tags): continue
      job_list.append(job)

    return job_list

  def add_job(self, run_script, partition = None, success_func = None, tags = None, parent_tags = None):
    job_counter = 0
    if len(self._job_counter) > 0:
      job_counter = list(self._job_counter)[-1]+1
    self._job_counter.add(job_counter)
    name = self._name+'_'+str(job_counter)
    run_script_name = self._write_script(run_script, name)
    log_name = self._log_folder+name
    job_partition = self._partition
    if partition: job_partition = partition
    job = Job(name, run_script_name, log_name, job_partition,
              success_func = success_func, tags = tags, parent_tags = parent_tags)
    self._jobs.append(job)
    if tags is not None:
      if isinstance(tags, list) or isinstance(tags, tuple):
        for tag in tags:
          if tag not in self._tagged_jobs: self._tagged_jobs[tag] = []
          self._tagged_jobs[tag].append(job)
      else:
        if tags not in self._tagged_jobs: self._tagged_jobs[tags] = []
        self._tagged_jobs[tags].append(job)

  # def add_jobs(self, n_jobs, run_script, run_args = None, partition = None):
  #   n_args = run_script.count('{}')
  #   if n_args > 0 and run_args is None:
  #     print ('You have to provide arguments to be used by the job')
  #     raise
  #   n_args_provided = len(run_args)
  #   if n_args > 1 and n_args_provided != n_args:
  #     print ('Job requires '+str(n_args)+' separate arguments, '+str(n_args_provided)+' were provided')
  #     raise
  #   run_args_resolved = []
  #   if n_args == 1:
  #     run_args = [run_args]

  #   if run_args is None: return 0
        
  #   for arg in run_args:
  #     if isinstance(arg, list) or isinstance(arg, tuple):
  #       len_arg = len(arg)
  #       if len_arg != n_jobs:
  #         print ('Length of argument list is '+str(len_arg)+', while '+str(n_jobs)+' are to be submitted')
  #         raise
  #       run_args_resolved.append(arg)
  #     else:
  #       arg_list = n_jobs * [arg]
  #       run_args_resolved.append(arg)

  #   job_partition = self._partition
  #   if partition: job_partition = partition

  #   for run_arg in zip(*run_args_resolved):
  #     job_run_script = run_script.format(*run_arg)
  #     self.add_job(job_run_script, job_partition)

  def _write_script(self, run_script, name):
    out_file_name = self._script_folder+name
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      if not run_script.startswith('#!'): out_file.write('#!/bin/bash \n')
      out_file.write(run_script)

    return out_file_name

  ## TODO: needs to be more robust, i.e. what happens if the parent_tag is not in the tagged jobs dict
  def _check_job_readiness(self, job):
    parent_tags = job.get_parent_tags()
    if not parent_tags:
      return True
    for tag in parent_tags:
      for tagged_job in self._tagged_jobs[tag]:
        status = tagged_job.get_status()
        if status == Status.Success: continue
        return False
    
    return True

  def run_jobs(self, intervall = 5):
    n_all = len(self._jobs)
    running = True
    while running:
      self.submit_jobs()
      status_dict = self._get_jobs_status()
      n_success = status_dict[Status.Success]
      n_failed = status_dict[Status.Failed]
      print_string = 'Jobs success/fail/all: ('+str(n_success)+'/'+str(n_failed)+'/'+str(n_all)+')'
      stdout.write('\r'+print_string)
      stdout.flush()
      time.sleep(intervall)
      if (n_success+n_failed) == n_all: running = False
    stdout.write('\n')

  def submit_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      if not self._check_job_readiness(job): continue
      job.submit()

  def cancel_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      job.cancel()

  ## TODO: must be rather check_jobs_status with some decision making if jobs failed (retry logic, maybe job can automatically gather on which machine it was running on)
  def _get_jobs_status(self):
    status_dict = {Status.Configured: 0, Status.Running: 0, Status.Finished: 0, Status.Success: 0, Status.Failed: 0, Status.Cancelled: 0}
    for job in self._jobs:
      status = job.get_status()
      status_dict[status] += 1

    return status_dict

  ## TODO: modify so that it allows to specify tags
  def check_status(self):
    status_dict = self._get_jobs_status()
    n_all = str(len(self._jobs))
    for status, n_jobs in status_dict.items():
      print (status.name+':', '('+str(n_jobs)+'/'+n_all+')')

  @staticmethod
  def _has_tag(job, tag):
    if tag in job.get_tags():
      return True
    else:
      return False

  @staticmethod
  def _has_tags(job, tags):
    ret_val = False
    if isinstance(tags, list) or isinstance(tags, tuple):
      for tag in tags:
        ret_val = JobHander._has_tag(job, tag)
        if ret_val: break
    else:
      ret_val = JobHander._has_tag(job, tags)

    return ret_val
