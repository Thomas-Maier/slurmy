
import slurmy
from slurmy import JobHandler
from slurmy import Slurm


def main():
    ## Backend here is set as a default
    jobHandler = JobHandler(backend = Slurm(partition = 'lsschaile'))

    run_script = """
    sleep {1}
    echo $1
    echo $2
    """

    run_args = [1, 2, 3, 4, 5, 6]
    times = [2, 4, 6, 8, 10, 12]

    for time_val, run_arg in zip(times, run_args):
        ## Backend here (or rather its configuration) overwrites the default set in the JobHandler instance
        ## This allows for job specific configuration of the backend
        jobHandler.add_job(backend = Slurm(partition = 'lsschaile'),
                           run_script = run_script.format(run_arg, time_val),
                           run_args = 'bla blub')

    ## Using already existing batch shell script
    example_script = '{}/examples/slurm_script.sh'.format(slurmy.__file__.rstrip('__init__.py'))
    ## This will use the default backend configuration at the top
    jobHandler.add_job(run_script = example_script,
                       run_args = 'bla blub')

    ## This will execute a continuous job submission which continues until all jobs are done
    ## The "interval" argument defines the frequency at which the job submission is executed (in seconds), or can be set to -1 to switch to manual update
    jobHandler.run_jobs(interval = 2)

if __name__ == '__main__':
    main()
