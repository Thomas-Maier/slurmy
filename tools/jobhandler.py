
from __future__ import print_function
import os
import time
from sys import stdout
from collections import OrderedDict
import pickle
import logging
from .defs import Status, Theme
from .job import Job, JobConfig
from .namegenerator import NameGenerator
from . import options as ops
from ..backends import get_backend
from .parser import Parser

log = logging.getLogger('slurmy')


class JobHandlerConfig:
  def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, is_verbose = False, success_func = None, max_retries = 0, theme = Theme.Lovecraft, run_max = None, do_snapshot = True):
    ## Static variables
    self._name_gen = NameGenerator(name = name, theme = theme)
    self.name = self._name_gen.name
    self.base_dir, self.script_dir, self.log_dir, self.output_dir, self.snapshot_dir, self.path = JobHandlerConfig.get_dirs(self.name, work_dir)
    self.success_func = success_func
    self.is_verbose = is_verbose
    self.local_max = local_max
    self.max_retries = max_retries
    self.run_max = run_max
    self.backend = backend
    self._do_snapshot = do_snapshot
    ## Dynamic variables
    self._jobs_configs = []
    self._job_states = {Status.Configured: set(), Status.Running: set(), Status.Finished: set(), Status.Success: set(), Status.Failed: set(), Status.Cancelled: set()}
    self._local_counter = 0

  @staticmethod
  def get_dirs(name, work_dir, script = 'scripts', log = 'logs', output = 'output', snapshot = 'snapshot', snapshot_name = 'JobHandlerConfig.pkl'):
    base_dir = '{}/'.format(name)
    if work_dir: base_dir = '{}/{}'.format(work_dir.rstrip('/'), base_dir)
    script_dir = '{}{}/'.format(base_dir, script)
    log_dir = '{}{}/'.format(base_dir, log)
    output_dir = '{}{}/'.format(base_dir, output)
    snapshot_dir = '{}{}/'.format(base_dir, snapshot)
    path = '{}{}'.format(snapshot_dir, snapshot_name)
    
    return base_dir, script_dir, log_dir, output_dir, snapshot_dir, path
    

class JobHandler:
  def __init__(self, name = None, backend = None, work_dir = '', local_max = 0, is_verbose = False, success_func = None, max_retries = 0, theme = Theme.Lovecraft, run_max = None, do_snapshot = True, use_snapshot = False, description = None):
    self._debug = False
    if log.level == 10: self._debug = True
    ## Variables that are not picklable
    self._jobs = {}
    self._tagged_jobs = {}
    self._local_jobs = []
    ## Backend setup
    if backend is None and ops.Main.backend is not None:
      backend = get_backend(ops.Main.backend)
    ## Snapshot loading
    if use_snapshot:
      if not name:
        log.error('Cannot use snapshot without a name')
        raise Exception()
      path = JobHandlerConfig.get_dirs(name, work_dir)[-1]
      if not os.path.isfile(path):
        log.error('Could not find path to snapshot')
        raise Exception()
      log.debug('Read snapshot from {}'.format(path))
      with open(path, 'rb') as in_file:
        self.config = pickle.load(in_file)
      log.debug('Read job snapshots')
      for job_config in self.config._jobs_configs:
        self._add_job_with_config(job_config)
    else:
      ## Make new JobHandler config
      self.config = JobHandlerConfig(name = name, backend = backend, work_dir = work_dir, local_max = local_max, is_verbose = is_verbose, success_func = success_func, max_retries = max_retries, theme = theme, run_max = run_max, do_snapshot = do_snapshot)
      self._reset()
      JobHandler._add_bookkeeping(self.config.name, work_dir, description)
    ## Variable parser
    self._parser = Parser(self.config)
      
  def __getitem__(self, key):
    return self._jobs[key]

  def _reset(self):
    log.debug('Reset JobHandler')
    if os.path.isdir(self.config.base_dir): os.system('rm -r '+self.config.base_dir)
    os.makedirs(self.config.script_dir)
    os.makedirs(self.config.log_dir)
    os.makedirs(self.config.output_dir)
    if os.path.isdir(self.config.snapshot_dir): os.system('rm -r '+self.config.snapshot_dir)
    os.makedirs(self.config.snapshot_dir)
    self._update_snapshot()

  def _update_snapshot(self, skip_jobs = False):
    ## If snapshotting is deactivated, do nothing
    if not self.config._do_snapshot: return
    if not skip_jobs:
      log.debug('Update job snapshots')
      for job in self._jobs.values():
        job.update_snapshot()
    log.debug('Update JobHandler snapshot')
    with open(self.config.path, 'wb') as out_file:
      pickle.dump(self.config, out_file)

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
    ## Ensure that a first snapshot is made
    if self.config._do_snapshot: job.update_snapshot()

    return job

  def add_job(self, backend = None, run_script = None, run_args = None, success_func = None, max_retries = None, output = None, tags = None, parent_tags = None):
    if backend is None and ops.Main.backend is not None:
      backend = get_backend(ops.Main.backend)
    if backend is None:
      log.error('No backend set for job, either set directly or define default in ~/.slurmy')
      return
    ## Set run_script and run_args if not already done
    backend.run_script = backend.run_script or run_script
    backend.run_args = backend.run_args or run_args
    ## Parse variables
    backend.run_script = self._parser.replace(backend.run_script)
    if output: output = self._parser.replace(output)
    name = self.config._name_gen.next()
    backend.name = name
    backend.write_script(self.config.script_dir)
    backend.log = self.config.log_dir+name
    backend.sync(self.config.backend)
    job_success_func = success_func or self.config.success_func
    job_max_retries = max_retries or self.config.max_retries
    config_path = self.config.snapshot_dir+name+'.pkl'

    job_config = JobConfig(backend, path = config_path, success_func = job_success_func, max_retries = job_max_retries, output = output, tags = tags, parent_tags = parent_tags)
    self.config._jobs_configs.append(job_config)
    ## Update snapshot to make sure job configs list is properly updated
    self._update_snapshot(skip_jobs = True)
      
    return self._add_job_with_config(job_config)

  def _job_ready(self, job):
    parent_tags = job.get_parent_tags()
    if not parent_tags:
      return True
    for tag in parent_tags:
      if tag not in self._tagged_jobs:
        log.error('Parent tag is not registered in jobs list!')
        continue
      for tagged_job in self._tagged_jobs[tag]:
        status = tagged_job.get_status()
        if status == Status.Success: continue
        ## If a parent job is uncoverably failed/cancelled, cancel this job as well
        if (status == Status.Failed or status == Status.Cancelled) and not tagged_job.do_retry(): job.cancel(clear_retry = True)
        return False
    
    return True

  def _get_print_string(self):
    print_string = 'Jobs '
    if self.config.is_verbose:
      n_running = len(self.config._job_states[Status.Running])
      n_local = len(self._local_jobs)
      n_batch = n_running - n_local
      print_string += 'running (batch/local/all): ({}/{}/{}); '.format(n_batch, n_local, n_running)
    n_success = len(self.config._job_states[Status.Success])
    n_failed = len(self.config._job_states[Status.Failed])
    n_all = len(self._jobs.values())
    print_string += '(success/fail/all): ({}/{}/{})'.format(n_success, n_failed, n_all)

    return print_string

  def _get_summary_string(self, time_spent = None):
    summary_dict = OrderedDict()
    summary_dict['all'] = {'string': 'Jobs processed ', 'batch': len(self._jobs.values())-self.config._local_counter, 'local': self.config._local_counter}
    summary_dict['success'] = {'string': '     successful ', 'batch': 0, 'local': 0}
    summary_dict['fail'] = {'string': '     failed ', 'batch': 0, 'local': 0}
    jobs_failed = ''
    for job in self._jobs.values():
      status = job.get_status()
      if status == Status.Success:
        if job.is_local():
          summary_dict['success']['local'] += 1
        else:
          summary_dict['success']['batch'] += 1
      elif status == Status.Failed or status == Status.Cancelled:
        jobs_failed += '{} '.format(job.get_name())
        if job.is_local():
          summary_dict['fail']['local'] += 1
        else:
          summary_dict['fail']['batch'] += 1

    print_string = ''
    for key, summary_val in summary_dict.items():
      if key == 'fail' and not jobs_failed: continue
      n_batch = summary_val['batch']
      n_local = summary_val['local']
      n_all = summary_val['batch'] + summary_val['local']
      print_string += '{}(batch/local/all): ({}/{}/{})\n'.format(summary_val['string'], n_batch, n_local, n_all)
    if self.config.is_verbose and jobs_failed:
      print_string += 'Failed jobs: {}\n'.format(jobs_failed)
    if time_spent:
      print_string += 'Time spent: {:.1f} s'.format(time_spent)

    return print_string

  def _wait_for_jobs(self, tags = None):
    for job in self.get_jobs(tags):
      if not job.is_local(): continue
      log.debug('Wait for job {}'.format(job.get_name()))
      job.wait()

  def _update_job_status(self, job):
    name = job.get_name()
    new_status = job.get_status()
    ## If old and new status are the same, do nothing
    if name in self.config._job_states[new_status]: return
    ## Remove current status entry for job
    for status in self.config._job_states.keys():
      if name not in self.config._job_states[status]: continue
      self.config._job_states[status].remove(name)
    ## Add new one
    self.config._job_states[new_status].add(name)

  def _update_job_states(self):
    for job in self._jobs.values():
      self._update_job_status(job)

  def print_summary(self, time_spent = None):
    print_string = self._get_summary_string(time_spent)
    stdout.write('\r'+print_string)
    stdout.write('\n')

  ## TODO: add retry option for interactive functionality (probably just incorporate in submit_jobs)
  ## TODO: also rerun option which just adds force = True to retry
  def run_jobs(self, interval = 5):
    time_now = time.time()
    try:
      n_all = len(self._jobs.values())
      running = True
      while running:
        self.submit_jobs(make_snapshot = False, wait = False)
        print_string = self._get_print_string()
        if not self._debug:
          stdout.write('\r'+print_string)
          stdout.flush()
        else:
          log.debug(print_string)
        n_success = len(self.config._job_states[Status.Success])
        n_failed = len(self.config._job_states[Status.Failed])
        n_cancelled = len(self.config._job_states[Status.Cancelled])
        if (n_success+n_failed+n_cancelled) == n_all: running = False
        time.sleep(interval)
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
      ## Get current job states
      self._update_job_states()
      ## Check local jobs progression
      self._check_local_jobs()
      for job in self.get_jobs(tags):
        ## Submit new jobs only if current number of running jobs is below maximum, if set
        if self.config.run_max and not (len(self.config._job_states[Status.Running]) < self.config.run_max):
          log.debug('Maximum number of running jobs reached, skip job submission')
          break
        status = job.get_status()
        if (status == Status.Failed or status == Status.Cancelled): job.retry(submit = False)
        ## If job is not in Configured state there is nothing to do
        if status != Status.Configured: continue
        ## Check if job is ready to be submitted
        if not self._job_ready(job): continue
        if len(self._local_jobs) < self.config.local_max:
          job.set_local()
          self._local_jobs.append(job)
          self.config._local_counter += 1
        job.submit()
        ## Update job status
        self._update_job_status(job)
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

  def check_status(self):
    self._update_job_states()
    print_string = self._get_print_string()
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
    if isinstance(tags, list) or isinstance(tags, tuple) or isinstance(tags, set):
      for tag in tags:
        ret_val = JobHander._has_tag(job, tag)
        if ret_val: break
    else:
      ret_val = JobHander._has_tag(job, tags)

    return ret_val

  @staticmethod
  def _add_bookkeeping(name, folder, description = None):
    pwd = os.environ['PWD']
    work_dir = folder
    if not work_dir.startswith('/'): work_dir = '{}/{}'.format(pwd.rstrip('/'), work_dir)
    ops.Main.add_bookkeeping(name, work_dir, description)
