
from __future__ import print_function
import os
import time
from sys import stdout
import multiprocessing as mp
from collections import OrderedDict
from slurmyDef import Status
from job import Job


class JobHandler:
  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs
  ## TODO: Currently not really working with jobs without any args
  ## TODO: Make default setting of stuff like partition and make optional to also define on job to job basis
  ## TODO: Can I ask slurm if currently there are free slots?
  ## TODO: Give option to set a maximum number of submitted jobs
  ## TODO PACKAGE: Add a script that takes the JobHandler base folder and can make basic checks for the jobs
  ## TODO: Extend dependencies between jobs and their parent jobs, e.g. use output names from parent in run_script (needs some rudimentary parsing)

  def __init__(self, name = 'hans', partition = None, local_max = 0, is_verbose = False):
    self._name = name
    self._script_folder = self._name+'/scripts/'
    self._log_folder = self._name+'/logs/'
    self._jobs = []
    self._tagged_jobs = {}
    self._job_counter = 0
    self._partition = partition
    self._local_max = local_max
    self._local_jobs = []
    self._local_counter = 0
    self._is_verbose = is_verbose
    self._reset()

  def _reset(self):
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
    self._job_counter += 1
    name = self._name+'_'+str(self._job_counter)
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

  ## TODO: needs to be more robust, i.e. what happens if the parent_tag is not in the tagged jobs dict.
  ## Put a check on this in submit_jobs?
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

  ## TODO: think of better information printing
  def _get_print_string(self, status_dict):
    print_string = 'Jobs '
    if self._is_verbose:
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
  def _get_summary_string(self, time_val):
    summary_dict = OrderedDict()
    summary_dict['all'] = {'string': 'Jobs processed ', 'slurm': len(self._jobs)-self._local_counter, 'local': self._local_counter}
    summary_dict['success'] = {'string': '     successful ', 'slurm': 0, 'local': 0}
    summary_dict['fail'] = {'string': '     failed ', 'slurm': 0, 'local': 0}
    for job in self._jobs:
      if job.get_status() == Status.Success:
        if job.is_local():
          summary_dict['success']['local'] += 1
        else:
          summary_dict['success']['slurm'] += 1
      else:
        if job.is_local():
          summary_dict['fail']['local'] += 1
        else:
          summary_dict['fail']['slurm'] += 1

    print_string = ''
    for summary_val in summary_dict.values():
      n_slurm = summary_val['slurm']
      n_local = summary_val['local']
      n_all = summary_val['slurm'] + summary_val['local']
      print_string += '{}(slurm/local/all): ({}/{}/{})\n'.format(summary_val['string'], n_slurm, n_local, n_all)
    print_string += 'time spent: {:.1f} s'.format(time_val)

    return print_string

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
      print_string = self._get_summary_string(time_now)
      stdout.write('\r'+print_string)
      stdout.write('\n')
      

  def submit_jobs(self, tags = None):
    ## Check local jobs progression
    self._check_local_jobs()
    for job in self.get_jobs(tags):
      ## If job is not in Configured state there is nothing to do
      if job.get_status() != Status.Configured: continue
      ## Check if job is ready to be submitted
      if not self._check_job_readiness(job): continue
      if len(self._local_jobs) < self._local_max:
        job.set_local()
        self._local_jobs.append(job)
        self._local_counter += 1
      job.submit()
      
  def cancel_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      ## Nothing to do when job is not in Running state
      if job.get_status() != Status.Running: continue
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
