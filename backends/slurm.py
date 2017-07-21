
import subprocess
import os
import shlex
import logging
from ..tools.defs import Status
from .base import Base
from ..tools import options as ops

log = logging.getLogger('slurmy')

## TODO: General check for backends needed, if their respective executables/binaries/whatever are present on the system, if not throw an error. Otherwise you only get a (to the user) cryptic subprocess exception (in the case of Slurm)
## TODO: add more sbatch options

class Slurm(Base):
  bid = 'Slurm'
  
  def __init__(self, name = None, log = None, partition = None, exclude = None, clusters = None, qos = None, run_script = None, run_args = None):
    self.name = name
    self.log = log
    self.partition = partition
    self.exclude = exclude
    self.clusters = clusters
    self.qos = qos
    self.run_script = run_script
    self.run_args = run_args
    ## shlex splits run_args in a Popen digestable way
    if isinstance(self.run_args, str): self.run_args = shlex.split(self.run_args)
    self.job_id = None
    ## Get default options
    ops.Main.get_backend_options(self)

  def write_script(self, script_folder):
    if os.path.isfile(self.run_script): return
    out_file_name = script_folder+self.name
    with open(out_file_name, 'w') as out_file:
      ## Required for slurm submission script
      if not self.run_script.startswith('#!'): out_file.write('#!/bin/bash \n')
      out_file.write(self.run_script)
    self.run_script = out_file_name

  def sync(self, config):
    if config is None or not isinstance(config, Slurm): return
    self.name = self.name or config.name
    self.log = self.log or config.log
    self.partition = self.partition or config.partition
    self.exclude = self.exclude or config.exclude
    self.clusters = self.clusters or config.clusters
    self.qos = self.qos or config.qos
    self.run_script = self.run_script or config.run_script
    self.run_args = self.run_args or config.run_args

  def submit(self):
    submit_list = ['sbatch']
    if self.name: submit_list += ['-J', self.name]
    if self.log: submit_list += ['-o', self.log]
    if self.partition: submit_list += ['-p', self.partition]
    if self.exclude: submit_list += ['-x', self.exclude]
    if self.clusters: submit_list += ['-M', self.clusters]
    if self.qos: submit_list += ['--qos', self.qos]
    submit_list.append(self.run_script)
    if self.run_args: submit_list += self.run_args
    log.debug('({}) Submit job with command {}'.format(self.name, submit_list))
    submit_string = subprocess.check_output(submit_list, universal_newlines = True)
    job_id = int(submit_string.split(' ')[-1].rstrip('\n'))
    self.job_id = job_id

    return job_id

  def cancel(self):
    log.debug('({}) Cancel job'.format(self.name))
    os.system('scancel {}'.format(self.job_id))

  ## TODO: probably more robust to use sacct to identify if job is still running, squeue -j throws an error after some time of waiting...
  def status(self):
    status_string = subprocess.check_output(['squeue', '-j', str(self.job_id)], universal_newlines = True)
    n_lines = status_string.count('\n')
    status = Status.Finished
    if n_lines > 1: status = Status.Running
      
    return status

  def exitcode(self):
    sacct_string = subprocess.check_output(['sacct', '-j', str(self.job_id), '-P', '-o', 'ExitCode'], universal_newlines = True)
    exitcode = sacct_string.split('\n')[1]

    return exitcode
