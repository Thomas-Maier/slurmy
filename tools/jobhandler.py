
from __future__ import print_function
import os
import time
from sys import stdout
from collections import OrderedDict
import pickle
import logging
from .defs import Status, NameGenerator
from .job import Job, JobConfig

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('slurmy')

name_gen = NameGenerator()


class JobHandlerConfig:
  def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, is_verbose = False, success_func = None, max_retries = 0):
    self.name = name
    ## For safety, if given name is emtpy set a default
    if not self.name: self.name = name_gen.get_name()
    self.base_folder = self.name+'/'
    if work_dir: self.base_folder = work_dir.rstrip('/')+self.name+'/'
    self.script_folder = self.base_folder+'scripts/'
    self.log_folder = self.base_folder+'logs/'
    self.output_folder = self.base_folder+'output/'
    self.snapshot_folder = self.base_folder+'/snapshot/'
    self.path = self.snapshot_folder+'JobHandlerConfig.pkl'
    self.jobs_configs = []
    self.job_counter = 0
    self.success_func = success_func
    self.local_max = local_max
    self.local_counter = 0
    self.is_verbose = is_verbose
    self.max_retries = max_retries
    self.backend = backend

class JobHandler:
  ## Generates Jobs according to configuration
  ## TODO: Can I ask slurm if currently there are free slots?
  ## TODO: Give option to set a maximum number of submitted jobs
  ## TODO: Extend dependencies between jobs and their parent jobs, e.g. use output names from parent in run_script (needs some rudimentary parsing)
  ## TODO: Output functionality for job and jobhandler: Define output for a job of which it should keep track of
  ## TODO: add_parent(job, parent_job) which automatically makes the appropriate parent_tags and tags setting, work with str or job object for job in order to use already added job or new one. Also allow for list of parent jobs and list of child jobs. Maybe just additional argument to add_job.
  ## TODO: print_summary should take into account that jobs could be unsubmitted/still running
  ## TODO: implement better debug printout machinery

  def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, is_verbose = False, success_func = None, max_retries = 0, use_snapshot = False):
    self._debug = False
    if log.level == 10: self._debug = True
    ## Variables that are not picklable
    self._jobs = {}
    self._tagged_jobs = {}
    self._local_jobs = []
    ## JobHandler config
    self._config = JobHandlerConfig(name = name, backend = backend, work_dir = work_dir, local_max = local_max, is_verbose = is_verbose, success_func = success_func, max_retries = max_retries)
    if use_snapshot and os.path.isfile(self._config.path):
      log.debug('Read snapshot from {}'.format(self._config.path))
      with open(self._config.path, 'rb') as in_file:
        self._config = pickle.load(in_file)
      log.debug('Read job snapshots')
      for job_config in self._config.jobs_configs:
        self._add_job_with_config(job_config)
    else:
      self._reset()

  def __getitem__(self, key):
    return self._jobs[key]

  def _reset(self):
    log.debug('Reset JobHandler')
    if os.path.isdir(self._config.base_folder): os.system('rm -r '+self._config.base_folder)
    os.makedirs(self._config.script_folder)
    os.makedirs(self._config.log_folder)
    if os.path.isdir(self._config.snapshot_folder): os.system('rm -r '+self._config.snapshot_folder)
    os.makedirs(self._config.snapshot_folder)

  def _update_snapshot(self):
    log.debug('Update job snapshots')
    for job in self._jobs.values():
      job.update_snapshot()
    log.debug('Update snapshot')
    with open(self._config.path, 'wb') as out_file:
      pickle.dump(self._config, out_file)

  def get_jobs(self, tags = None):
    job_list = []
    for job in self._jobs.values():
      if tags is not None and not JobHandler._has_tags(job, tags): continue
      job_list.append(job)

    return job_list

  def _add_job_with_config(self, job_config):
    log.debug('Add job {}'.format(job_config.name))
    job = Job(config = job_config)
    self._jobs[job.get_name()] = job
    tags = job_config.tags
    if tags is not None:
      if isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set):
        for tag in tags:
          if tag not in self._tagged_jobs: self._tagged_jobs[tag] = []
          self._tagged_jobs[tag].append(job)
      else:
        if tags not in self._tagged_jobs: self._tagged_jobs[tags] = []
        self._tagged_jobs[tags].append(job)

    return job

  def add_job(self, backend, success_func = None, max_retries = None, tags = None, parent_tags = None):
    self._config.job_counter += 1
    name = '{}_{}'.format(self._config.name, self._config.job_counter)
    backend.name = name
    backend.write_script(self._config.script_folder)
    backend.log = self._config.log_folder+name
    backend.sync(self._config.backend)
    job_success_func = success_func or self._config.success_func
    job_max_retries = max_retries or self._config.max_retries
    config_path = self._config.snapshot_folder+name+'.pkl'

    job_config = JobConfig(backend, path = config_path, success_func = job_success_func, max_retries = job_max_retries, tags = tags, parent_tags = parent_tags)
    self._config.jobs_configs.append(job_config)
    with open(job_config.path, 'wb') as out_file:
      pickle.dump(job_config, out_file)
      
    return self._add_job_with_config(job_config)

  ## TODO: needs to be more robust, i.e. what happens if the parent_tag is not in the tagged jobs dict.
  ## Put a check on this in submit_jobs?
  def _job_ready(self, job):
    parent_tags = job.get_parent_tags()
    if not parent_tags:
      return True
    for tag in parent_tags:
      if tag not in self._tagged_jobs:
        log.warning('Parent tag is not registered in jobs list!')
        continue
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
    n_all = len(self._jobs.values())
    print_string += '(success/fail/all): ({}/{}/{})'.format(n_success, n_failed, n_all)

    return print_string

  ## TODO: better print format
  def _get_summary_string(self, time_spent = None):
    summary_dict = OrderedDict()
    summary_dict['all'] = {'string': 'Jobs processed ', 'slurm': len(self._jobs.values())-self._config.local_counter, 'local': self._config.local_counter}
    summary_dict['success'] = {'string': '     successful ', 'slurm': 0, 'local': 0}
    summary_dict['fail'] = {'string': '     failed ', 'slurm': 0, 'local': 0}
    jobs_failed = ''
    for job in self._jobs.values():
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

  def _wait_for_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      if not job.is_local(): continue
      log.debug('Wait for job {}'.format(job.get_name()))
      job.wait()

  def print_summary(self, time_spent = None):
    print_string = self._get_summary_string(time_spent)
    stdout.write('\r'+print_string)
    stdout.write('\n')

  def run_jobs(self, interval = 5):
    time_now = time.time()
    try:
      n_all = len(self._jobs.values())
      running = True
      while running:
        self.submit_jobs(make_snapshot = False, wait = False)
        status_dict = self._get_jobs_status()
        print_string = self._get_print_string(status_dict)
        if not self._debug:
          stdout.write('\r'+print_string)
          stdout.flush()
        else:
          log.debug(print_string)
        time.sleep(interval)
        n_success = status_dict[Status.Success]
        n_failed = status_dict[Status.Failed]
        n_cancelled = status_dict[Status.Cancelled]
        if (n_success+n_failed+n_cancelled) == n_all: running = False
    except KeyboardInterrupt:
      if not self._debug: stdout.write('\n')
      log.warning('Quitting gracefully...')
      try:
        log.warning('Waiting for local jobs, ctrl+c again to cancel them...')
        self._wait_for_jobs()
      except KeyboardInterrupt:
        log.warning('Cancel local jobs...')
        ## Need to cancel cleanly, since jobs are setup to ignore signals to parent process
        self.cancel_jobs(only_local = True, make_snapshot = False)
    except:
      ## If something explodes, cancel all running jobs
      self.cancel_jobs(make_snapshot = False)
      raise
    finally:
      ## Final snapshot
      self._update_snapshot()
      time_now = time.time() - time_now
      if not self._debug: self.print_summary(time_now)

  def submit_jobs(self, tags = None, make_snapshot = True, wait = True):
    try:
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
      if wait: self._wait_for_jobs(tags)
      if make_snapshot: self._update_snapshot()
    except:
      ## If something explodes, cancel all running jobs
      self.cancel_jobs(make_snapshot = False)
      raise
      
  def cancel_jobs(self, tags = None, only_local = False, only_batch = False, make_snapshot = True):
    for job in self.get_jobs(tags):
      ## Nothing to do when job is not in Running state
      if job.get_status() != Status.Running: continue
      if only_local and not job.is_local(): continue
      if only_batch and job.is_local(): continue
      job.cancel()
    if make_snapshot: self._update_snapshot()

  def retry_jobs(self, tags = None, make_snapshot = True):
    try:
      for job in self.get_jobs(tags):
        ## Retry only if job is failed or cancelled
        if job.get_status() != Status.Failed and job.get_status() != Status.Cancelled: continue
        job.retry()
      if make_snapshot: self._update_snapshot()
    except:
      ## If something explodes, cancel all running jobs
      self.cancel_jobs(make_snapshot = False)
      raise

  def _get_jobs_status(self):
    status_dict = {Status.Configured: 0, Status.Running: 0, Status.Finished: 0, Status.Success: 0, Status.Failed: 0, Status.Cancelled: 0}
    for job in self._jobs.values():
      status = job.get_status()
      status_dict[status] += 1

    return status_dict

  ## TODO: modify so that it allows to specify tags
  def check_status(self):
    status_dict = self._get_jobs_status()
    print_string = self._get_print_string(status_dict)
    print (print_string)

  def _check_local_jobs(self):
    for i, job in enumerate(self._local_jobs):
      if job.get_status() == Status.Running: continue
      self._local_jobs.pop(i)

  def jobs(self, tag = None):
    for job_name, job in self._jobs.items():
      if tag and tag not in job.get_tags(): continue
      print ('Job "{}": {}'.format(job.get_name(), job.get_status().name))

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
