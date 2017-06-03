#!/usr/bin/env python


class Job:

  ## Should know about all information that it needs to run a single slurm job
  ## Checks itself if it was successful (by whatever means that are defined)
  ## Is able to submit as slurm job or run locally

  def __init__(self):

    self._input = 

    return None


class JobHandler:

  ## Generates Jobs according to configuration
  ## Allow for arbitrary combination of slurm jobs and local (multiprocessing) jobs

  def __init__(self):

    return None

  def _submit_job(self):
    return 0

  def _config_job(self):
    return 0


if __name__ == '__main__':
  pass
