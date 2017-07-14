
import subprocess
import os
from slurmyDef import Status


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
