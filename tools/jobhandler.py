
import os
import subprocess


def slurm_submit(job_name, log_name, partition, run_script):
  submit_string = 'sbatch -J {} -o {} -p {} {}'.format(job_name, log_name, partition, run_script)
  os.system(submit_string)
  # -x exlude
  # -M clusters
  # -M lcg -p lcg_serial --qos=lcg_add

def slurm_cancel(job_name):
  cancel_string = 'scancel -n {}'.format(job_name)
  os.system(cancel_string)

def slurm_status(job_name):
  status_string = subprocess.check_output(['squeue', '-n', job_name])
  n_lines = status_string.count('\n')
  status = 'finished'
  if n_lines > 1:
    status = 'running'

  return status
  


class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self, name, run_script, log_file, partition, success_func = None):
    self._name = name
    self._run_script = run_script
    self._log_file = log_file
    self._partition = partition
    ## TODO: need central def file with enums
    self._status = 'configured'

    ## Default: look at return code of slurm jobs?
    def dummy():
      return True
    self._success_func = dummy
    if success_func is not None: self._success_func = success_func

  def submit(self):
    slurm_submit(self._name, self._log_file, self._partition, self._run_script)

  def cancel(self):
    slurm_cancel(self._name)

  def get_status(self):
    if self._status != 'finished':
      self._status = slurm_status(self._name)
    
    return self._status

  def get_success(self):
    success = False
    if self._status == 'finished':
      success = self._success_func()
      
    return success


class JobHandler:

  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs
  ## TODO: Currently not really working with jobs without any args
  ## TODO: Rather make the job config adding a function (add job by job) and the in one swoop functionality optional
  ## TODO: Make default setting of stuff like partition and make optional to also define on job to job basis

  def __init__(self, name = None, partition = None):
    self._name = 'hans'
    if name: self._name = name
    self._script_folder = 'scripts_'+self._name+'/'
    self._log_folder = 'logs_'+self._name+'/'
    self._jobs = {}
    self._job_ids = set()
    self._partition = None
    if partition: self._partition = partition
    self.reset()

  def reset(self):
    if os.path.isdir(self._script_folder): os.system('rm -r '+self._script_folder)
    os.mkdir(self._script_folder)
    if os.path.isdir(self._log_folder): os.system('rm -r '+self._log_folder)
    os.mkdir(self._log_folder)

  def add_job(self, run_script, partition = None, success_func = None):
    job_id = 0
    if len(self._job_ids) > 0:
      job_id = list(self._job_ids)[-1]+1
    self._job_ids.add(job_id)
    job_name = self._name+'_'+str(job_id)
    run_script_name = self._write_script(run_script, job_name)
    log_name = self._log_folder+job_name
    job_partition = self._partition
    if partition: job_partition = partition
    job = Job(job_name, run_script_name, log_name, job_partition)
    self._jobs[job_name] = job

  def add_jobs(self, n_jobs, run_script, run_args = None, partition = None):
    n_args = run_script.count('{}')
    if n_args > 0 and run_args is None:
      print ('You have to provide arguments to be used by the job')
      raise
    n_args_provided = len(run_args)
    if n_args > 1 and n_args_provided != n_args:
      print ('Job requires '+str(n_args)+' seperate arguments, '+str(n_args_provided)+' were provided')
      raise
    run_args_resolved = []
    if n_args == 1:
      run_args = [run_args]

    if run_args is None: return 0
        
    for arg in run_args:
      if isinstance(arg, list) or isinstance(arg, tuple):
        len_arg = len(arg)
        if len_arg != n_jobs:
          print ('Length of argument list is '+str(len_arg)+', while '+str(n_jobs)+' are to be submitted')
          raise
        run_args_resolved.append(arg)
      else:
        arg_list = n_jobs * [arg]
        run_args_resolved.append(arg)

    job_partition = self._partition
    if partition: job_partition = partition

    for run_arg in zip(*run_args_resolved):
      job_run_script = run_script.format(*run_arg)
      self.add_job(job_run_script, job_partition)

  # def setup_jobs(self):
  #   self.reset()
  #   for i, run_arg in enumerate(zip(*self._run_args)):
  #     name = self._name+'_'+str(i)
  #     run_script = self._run_script.format(*run_arg)
  #     run_script_name = self._write_script(run_script, name)
  #     log_name = self._log_folder+name
  #     job = Job(name, run_script_name, log_name, self._partition)
  #     self._jobs[name] = job
  #     self._job_ids.add(i)

  def _write_script(self, run_script, name):
    out_file_name = self._script_folder+name
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      if not run_script.startswith('#!'): out_file.write('#!/bin/bash \n')
      out_file.write(run_script)

    return out_file_name

  def submit_jobs(self):
    for job in self._jobs.values():
      job.submit()

  def cancel_jobs(self):
    for job in self._jobs.values():
      job.cancel()

  def check_jobs_status(self):
    n_finished = 0
    n_all = len(self._jobs)
    for job in self._jobs.values():
      if job.get_status() != 'finished': continue
      n_finished += 1
    print ('Jobs finished/all:', '('+str(n_finished)+'/'+str(n_all)+')')

  def check_jobs_success(self):
    n_success = 0
    n_finished = 0
    n_all = len(self._jobs)
    for job in self._jobs.values():
      if job.get_status() != 'finished': continue
      n_finished += 1
      if not job.get_success(): continue
      n_success += 1
    print ('Jobs successful/finished/all:', '('+str(n_success)+'/'+str(n_finished)+'/'+str(n_all)+')')
