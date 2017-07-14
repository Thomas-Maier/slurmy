#!/usr/bin/env python

from tools.jobhandler import JobHandler


def main():
  name = 'hans'
  partition = 'lsschaile'
  local_max = 3

  jobHandler = JobHandler(name = name,
                          partition = partition,
                          local_max = local_max,
                          is_verbose = False)

  run_script = """
  echo "hi {0}" > out.{0}
  sleep {1}
  """
  
  run_args = [1, 2, 3, 4, 5, 6]
  times = [10, 20, 30, 40, 50, 60]

  for time_val, run_arg in zip(times, run_args):
    jobHandler.add_job(run_script.format(run_arg, time_val), tags = 'first')

  run_script = """
  ls out.{0}
  cat out.{0}
  """

  for run_arg in run_args:
    jobHandler.add_job(run_script.format(run_arg), tags = 'second', parent_tags = 'first')
    
  jobHandler.run_jobs(intervall = 2)

  return jobHandler


if __name__ == '__main__':
  jobHandler = main()
