#!/usr/bin/env python

from slurmy import JobHandler
from slurmy import Slurm


def main():
    jobHandler = JobHandler()

    run_script = """
    sleep {1}
    echo $1
    echo $2
    """

    run_args = [1, 2, 3, 4, 5, 6]
    times = [2, 4, 6, 8, 10, 12]

    for time_val, run_arg in zip(times, run_args):
        jobHandler.add_job(run_script = run_script.format(run_arg, time_val),
                           run_args = 'bla blub',
                           tags = 'first')

    for time_val, run_arg in zip(times, run_args):
        jobHandler.add_job(run_script = run_script.format(run_arg, time_val),
                           run_args = 'bla blub',
                           parent_tags = 'first')

    jobHandler.run_jobs(interval = 2)

if __name__ == '__main__':
    main()
