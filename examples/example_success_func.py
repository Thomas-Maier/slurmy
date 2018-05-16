#!/usr/bin/env python

from slurmy import JobHandler
from slurmy.backends import Slurm
from slurmy.tools.utils import SuccessOutputFile

def main():
    ## Success function, which has to be an instance of a class with __call__ defined
    jobHandler = JobHandler(success_func = SuccessOutputFile())

    ## Strings of the form @SLURMY.XYZ will be substituted with the respective definition in the JobHandler config, if XYZ is a variable of the config
    run_script = """
    sleep {1}
    echo "hi {0}" > @SLURMY.output_dir/out.{0}
    echo $1
    echo $2
    """

    run_args = [1, 2, 3, 4, 5, 6]
    times = [2, 4, 6, 8, 10, 12]

    for time_val, run_arg in zip(times, run_args):
        jobHandler.add_job(run_script = run_script.format(run_arg, time_val),
                           run_args = 'bla blub',
                           ## Set the output of the job
                           ## This can be anything (string, list, dict), since it's not used by the job itself
                           output = '@SLURMY.output_dir/out.{}'.format(run_arg),
                           ## Can overwrite default set for the JobHandler
                           success_func = SuccessOutputFile())

    jobHandler.run_jobs(interval = 2)

if __name__ == '__main__':
    main()
