
from __future__ import print_function
import os
import time
from sys import stdout
import multiprocessing as mp
from collections import OrderedDict
import pickle
from slurmyDef import Status
from job import Job, JobConfig


class JobHandlerConfig:
  def __init__(self, name = 'hans', work_dir = '', local_max = 0, is_verbose = False, partition = None, success_func = None, max_retries = 0):
    self.name = name
    ## For safety, if given name is emtpy set a default
    if not self.name: self.name = 'hans'
    self.base_folder = self.name+'/'
    if work_dir: self.base_folder = work_dir.rstrip('/')+self.name+'/'
    self.script_folder = self.base_folder+'scripts/'
    self.log_folder = self.base_folder+'logs/'
    self.output_folder = self.base_folder+'output/'
    self.snapshot_folder = self.base_folder+'/snapshot/'
    self.path = self.snapshot_folder+'JobHandlerConfig.pkl'
    self.jobs_configs = []
    self.job_counter = 0
    self.partition = partition
    self.success_func = success_func
    self.local_max = local_max
    self.local_counter = 0
    self.is_verbose = is_verbose
    self.max_retries = max_retries

class JobHandler:
  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs
  ## TODO: Currently not really working with jobs without any args
  ## TODO: Make default setting of stuff like partition and make optional to also define on job to job basis
  ## TODO: Can I ask slurm if currently there are free slots?
  ## TODO: Give option to set a maximum number of submitted jobs
  ## TODO PACKAGE: Add a script that takes the JobHandler base folder and can make basic checks for the jobs
  ## TODO: Extend dependencies between jobs and their parent jobs, e.g. use output names from parent in run_script (needs some rudimentary parsing)
  ## TODO: Output functionality for job and jobhandler: Define output for a job of which it should keep track of
  ## TODO: Allow for predefined command line script with arguments to be submitted

  def __init__(self, use_snapshot = False, name = 'hans', work_dir = '', local_max = 0, is_verbose = False, partition = None, success_func = None, max_retries = 0):
    ## Variables that are not picklable
    self._jobs = []
    self._tagged_jobs = {}
    self._local_jobs = []
    ## JobHandler config
    self._config = JobHandlerConfig(name = name, work_dir = work_dir, local_max = local_max, is_verbose = is_verbose, partition = partition, success_func = success_func,
                                    max_retries = max_retries)
    if use_snapshot and os.path.isfile(self._config.path):
      with open(self._config.path, 'rb') as in_file:
        self._config = pickle.load(in_file)
      if self._config.local_max > 0 or local_max > 0:
        print ('Snapshot usage and local processing is not compatible...')
        raise
      for job_config in self._config.jobs_configs:
        self._add_job_with_config(job_config)
    else:
      self._reset()

  def _reset(self):
    if os.path.isdir(self._config.base_folder): os.system('rm -r '+self._config.base_folder)
    os.makedirs(self._config.script_folder)
    os.makedirs(self._config.log_folder)
    if os.path.isdir(self._config.snapshot_folder): os.system('rm -r '+self._config.snapshot_folder)
    os.makedirs(self._config.snapshot_folder)

  def _update_snapshot(self):
    with open(self._config.path, 'wb') as out_file:
      pickle.dump(self._config, out_file)

  ## TODO: Make this a generator instead
  def get_jobs(self, tags = None):
    job_list = []
    for job in self._jobs:
      if tags is not None and not JobHandler._has_tags(job, tags): continue
      job_list.append(job)

    return job_list

  def _add_job_with_config(self, job_config):
    job = Job(config = job_config)
    self._jobs.append(job)
    tags = job_config.tags
    if tags is not None:
      if isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set):
        for tag in tags:
          if tag not in self._tagged_jobs: self._tagged_jobs[tag] = []
          self._tagged_jobs[tag].append(job)
      else:
        if tags not in self._tagged_jobs: self._tagged_jobs[tags] = []
        self._tagged_jobs[tags].append(job)    

  def add_job(self, run_script, run_args = None, partition = None, success_func = None, max_retries = None, tags = None, parent_tags = None):
    self._config.job_counter += 1
    name = self._config.name+'_'+str(self._config.job_counter)
    run_script_name = run_script
    if not os.path.isfile(run_script_name):
      run_script_name = self._write_script(run_script, name)
    log_name = self._config.log_folder+name
    job_partition = partition or self._config.partition
    job_success_func = success_func or self._config.success_func
    job_max_retries = max_retries or self._config.max_retries
    config_path = self._config.snapshot_folder+name+'.pkl'

    job_config = JobConfig(name = name, path = config_path, run_script = run_script_name, run_args = run_args, log_file = log_name, partition = job_partition,
                           success_func = job_success_func, max_retries = job_max_retries, tags = tags, parent_tags = parent_tags)
    self._config.jobs_configs.append(job_config)
    with open(job_config.path, 'wb') as out_file:
      pickle.dump(job_config, out_file)
    self._add_job_with_config(job_config)

  def _write_script(self, run_script, name):
    out_file_name = self._config.script_folder+name
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      if not run_script.startswith('#!'): out_file.write('#!/bin/bash \n')
      out_file.write(run_script)

    return out_file_name

  ## TODO: needs to be more robust, i.e. what happens if the parent_tag is not in the tagged jobs dict.
  ## Put a check on this in submit_jobs?
  def _job_ready(self, job):
    parent_tags = job.get_parent_tags()
    if not parent_tags:
      return True
    for tag in parent_tags:
      for tagged_job in self._tagged_jobs[tag]:
        status = tagged_job.get_status()
        if status == Status.Success: continue
        ## If a parent job is uncoverably failed/cancelled, cancel this job as well
        if (status == Status.Failed or status == Status.Cancelled) and not tagged_job.do_retry(): job.cancel(clear_retry = True)
        return False
    
    return True

  ## TODO: think of better information printing
  def _get_print_string(self, status_dict):
    print_string = 'Jobs '
    if self._config.is_verbose:
      n_local = len(self._local_jobs)
      n_running = status_dict[Status.Running]
      n_slurm = n_running - n_local
      print_string += 'running (slurm/local/all): ({}/{}/{}); '.format(n_slurm, n_local, n_running)
    n_success = status_dict[Status.Success]
    n_failed = status_dict[Status.Failed]
    n_all = len(self._jobs)
    print_string += '(success/fail/all): ({}/{}/{})'.format(n_success, n_failed, n_all)

    return print_string

  ## TODO: better print format
  def _get_summary_string(self, time_spent = None):
    summary_dict = OrderedDict()
    summary_dict['all'] = {'string': 'Jobs processed ', 'slurm': len(self._jobs)-self._config.local_counter, 'local': self._config.local_counter}
    summary_dict['success'] = {'string': '     successful ', 'slurm': 0, 'local': 0}
    summary_dict['fail'] = {'string': '     failed ', 'slurm': 0, 'local': 0}
    jobs_failed = ''
    for job in self._jobs:
      status = job.get_status()
      if status == Status.Success:
        if job.is_local():
          summary_dict['success']['local'] += 1
        else:
          summary_dict['success']['slurm'] += 1
      elif status == Status.Failed or status == Status.Cancelled:
        jobs_failed += '{} '.format(job.get_name())
        if job.is_local():
          summary_dict['fail']['local'] += 1
        else:
          summary_dict['fail']['slurm'] += 1

    print_string = ''
    for key, summary_val in summary_dict.items():
      if key == 'fail' and not jobs_failed: continue
      n_slurm = summary_val['slurm']
      n_local = summary_val['local']
      n_all = summary_val['slurm'] + summary_val['local']
      print_string += '{}(slurm/local/all): ({}/{}/{})\n'.format(summary_val['string'], n_slurm, n_local, n_all)
    if self._config.is_verbose and jobs_failed:
      print_string += 'Failed jobs: {}\n'.format(jobs_failed)
    if time_spent:
      print_string += 'time spent: {:.1f} s'.format(time_spent)

    return print_string

  def print_summary(self, time_spent = None):
    print_string = self._get_summary_string(time_spent)
    stdout.write('\r'+print_string)
    stdout.write('\n')

  def run_jobs(self, intervall = 5):
    time_now = time.time()
    try:
      n_all = len(self._jobs)
      running = True
      while running:
        self.submit_jobs()
        status_dict = self._get_jobs_status()
        print_string = self._get_print_string(status_dict)
        stdout.write('\r'+print_string)
        stdout.flush()
        time.sleep(intervall)
        n_success = status_dict[Status.Success]
        n_failed = status_dict[Status.Failed]
        n_cancelled = status_dict[Status.Cancelled]
        if (n_success+n_failed+n_cancelled) == n_all: running = False
    except KeyboardInterrupt:
      stdout.write('\n')
      print ('Quitting gracefully...')
      self.cancel_jobs()
      exit(0)
    finally:
      time_now = time.time() - time_now
      self.print_summary(time_now)
      

  def submit_jobs(self, tags = None):
    ## Check local jobs progression
    self._check_local_jobs()
    for job in self.get_jobs(tags):
      status = job.get_status()
      if (status == Status.Failed or status == Status.Cancelled): job.retry(submit = False)
      ## If job is not in Configured state there is nothing to do
      if status != Status.Configured: continue
      ## Check if job is ready to be submitted
      if not self._job_ready(job): continue
      if len(self._local_jobs) < self._config.local_max:
        job.set_local()
        self._local_jobs.append(job)
        self._config.local_counter += 1
      job.submit()
    self._update_snapshot()
      
  def cancel_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      ## Nothing to do when job is not in Running state
      if job.get_status() != Status.Running: continue
      job.cancel()

  def retry_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      ## Retry only if job is failed or cancelled
      if job.get_status() != Status.Failed and job.get_status() != Status.Cancelled: continue
      job.retry()

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

  def _check_local_jobs(self):
    for i, job in enumerate(self._local_jobs):
      if job.get_status() == Status.Running: continue
      self._local_jobs.pop(i)
      

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
