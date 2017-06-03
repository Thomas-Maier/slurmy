
import os


def slurm_submit(job_name, log_name, partition, run_script):
  submit_string = 'sbatch -J {} -o {} -p {} {}'.format(job_name, log_name, partition, run_script)
  os.system(submit_string)
  # -x exlude
  # -M clusters
  # -M lcg -p lcg_serial --qos=lcg_add

def slurm_cancel(job_name):
  cancel_string = 'scancel -n {}'.format(job_name)
  os.system(cancel_string)


class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self, name, run_script, log_file, partition):
    self._name = name
    self._run_script = run_script
    self._log_file = log_file
    self._partition = partition

  def submit(self):
    slurm_submit(self._name, self._log_file, self._partition, self._run_script)

  def cancel(self):
    slurm_cancel(self._name)


class JobHandler:

  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs

  def __init__(self, n_jobs, run_script, run_args = None, name = None):
    self._name = 'hans'
    if name: self._name = name
    self._jobs = []
    self._run_script = run_script

    self._script_folder = 'scripts_'+self._name+'/'
    self._log_folder = 'logs_'+self._name+'/'

    ## Check if run arguments are valid
    n_args = run_script.count('{}')
    if n_args > 0 and run_args is None:
      print ('You have to provide arguments to be used by the job')
      raise
    n_args_provided = len(run_args)
    if n_args > 1 and n_args_provided != n_args:
      print ('Job requires '+str(n_args)+' seperate arguments, '+str(n_args_provided)+' were provided')
      raise
    self._run_args = []
    if n_args == 1:
      run_args = [run_args]
        
    for arg in run_args:
      if isinstance(arg, list) or isinstance(arg, tuple):
        len_arg = len(arg)
        if len_arg != n_jobs:
          print ('Length of argument list is '+str(len_arg)+', while '+str(n_jobs)+' are to be submitted')
          raise
        self._run_args.append(arg)
      else:
        arg_list = n_jobs * [arg]
        self._run_args.append(arg)

  def setup_jobs(self):
    if os.path.isdir(self._script_folder):
      os.system('rm -r '+self._script_folder)
    os.mkdir(self._script_folder)
    print self._run_args
    for i, run_arg in enumerate(zip(*self._run_args)):
      name = self._name+'_'+str(i)
      run_script = self._run_script.format(*run_arg)
      run_script_name = self._write_script(run_script, name)
      log_name = self._log_folder+name
      job = Job(run_script_path)
      self._jobs.append(job)

  def _write_script(self, run_script, name):
    out_file_name = self._script_folder+name
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      out_file.write('#!/bin/bash \n')
      out_file.write(run_script)

    return out_file_name

  def submit_jobs(self):
    for job in self._jobs:
      job.submit()

  def cancel_jobs(self):
    for job in self._jobs:
      job.cancel()
