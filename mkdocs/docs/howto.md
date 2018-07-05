
## General Usage

You can just write a piece of python code that imports the required slurmy classes (e.g. [JobHandler](classes/JobHandler.md) and the backend class of your choice), defines jobs and calls the job submission. Job execution definitions can either be provided by already written batch shell scripts, or by defining the content of the shell script directly in your python code. For both cases, arguments that should be passed upon the execution to the scripts can also be specified.

Below you'll find several examples of how your job configuration script can look like. You should also have a look at the [interactive slurmy](interactive_slurmy.md) section to get an idea what you can do. Make sure to also take a look at the documentation of [JobHandler](classes/JobHandler.md), in particular [JobHandler.add_job()](classes/JobHandler.md#add_job).

<a name="slurmyconfig"></a>
## What you want to do before doing anything else

You can (and should) specify a slurmy config file, which defines your default configuration of relevant slurmy properties. In particular you can define which batch system backend you want to use and how it should be configured. This safes you from having to specify this every single time you want to use slurmy.

You just need to create a file `~/.slurmy` with this content (which you might want to modify):

```shell
bookkeeping = ~/.slurmy_bookkeeping
workdir = ./
backend = Slurm
editor = emacs -nw
## Slurm backend options
Slurm.partition = lsschaile
#Slurm.clusters = 
#Slurm.qos = 
#Slurm.exclude =
#Slurm.mem =
#Slurm.time =
#Slurm.export =
```

<a name="snapshots"></a>
## Snapshots

By default, slurmy will do bookkeeping of past [JobHandler](classes/JobHandler.md) sessions. The information is stored in a json file, which is defined in the slurmy config. Snapshot making can be deactivated by passing the respective argument to [JobHandler](classes/JobHandler.md#JobHandler).

Snapshot making is very useful, in particular if you want to make use of [interactive slurmy](interactive_slurmy.md).

## Simple example

```python
from slurmy import JobHandler

## Set up the JobHandler
jh = JobHandler()
## Define the run script content
run_script = """
echo "hans"
"""
## Add a job
jh.add_job(run_script = run_script)
## Run all jobs
jh.run_jobs()
```

### With explicit backend definition

If you don't create a slurmy config file specifying the batch system backend to use, or if you want to specify backends for each job, then you can do the following.

```python
from slurmy import JobHandler, Slurm

## Set up the backend
slurm = Slurm(partition = 'lsschaile')
## Set up the JobHandler
jh = JobHandler(backend = slurm)
## Define the run script content
run_script = """
echo "hans"
"""
## Add a job
### The backend can be individually set for each job
slurm_job = Slurm(partition = 'lsschaile', mem = '6000mb')
jh.add_job(backend = slurm_job, run_script = run_script)
## Run all jobs
jh.run_jobs()
```

## Using an already existing script file (with optional arguments)

You can also just use an existing script file. In this case you just specify the file path as `run_script`. You can also specify additional arguments to be passed to the run script.

```python
from slurmy import JobHandler

## Set up the JobHandler
jh = JobHandler()
## Specify path to run script on disk
run_script = '/path/to/run_script'
## Additional arguments to be passed to the run script
run_args = 'hans horst'
## Add a job
jh.add_job(run_script = run_script, run_args = run_args)
## Run all jobs
jh.run_jobs()
```

## Chaining Jobs with Tags

Jobs can be connected by adding tags and parent tags to them. Jobs with parent tags X,Y, and Z will only be executed if all jobs that have the tags X, Y, or Z have successfully finished.

```python
from slurmy import JobHandler

## Set up the JobHandler
jh = JobHandler()
## Define the run script content of job 1
run_script_1 = """
sleep 10
echo "hans"
"""
## Add job 1 with tag "hans"
jh.add_job(run_script = run_script_1, tags = 'hans')
## Define the run script content of job 2
run_script_2 = """
echo "horst"
"""
## Add job 2 with parent_tag "hans"
jh.add_job(run_script = run_script_2, parent_tags = 'hans')
## Run all jobs
jh.run_jobs()
```

## Steering evaluation of jobs processing status

By default, the exitcode of the job (either taken from the local process or from the batch system bookkeeping) is taken to determine if it finished and was successful or not. However, you can change how slurmy will evaluate whether the job is finished or was successful.

### Job listener

First a word on what the default evaluation setup of slurmy is. In general, jobs are designed to do their status evaluations themselves, i.e. the [JobHandler](classes/JobHandler.md) asks the job for it's status. This can get very performance heavy if this is connected to a request to the batch system accounting/bookkeeping. By default, slurmy runs a [Listener](classes/Listener.md) to collect the job information from the batch system and set it's exitcode when it's finished. Keep in mind that setting a `finished_func` (see below) will deactivate the listener and possibly slow down the job submission cycle (if you do something processing intensive for the evaluation).

### Define output file for success evaluation
You can define the `output` of each job explicitly to change the success evaluation to check for the output to be present. From a technical side, this sets up a [Listener](classes/Listener.md) which checks if the defined output files exist and sets the associated jobs status to SUCCESS if it finds them.

```python
from slurmy import JobHandler

## Set up the JobHandler
jh = JobHandler(output_max_attempts = 5)
## Define the run script content
run_script = """
touch ~/hans.txt
"""
## Add a job, specifying the output of the job.
jh.add_job(run_script = run_script, output = '~/hans.txt')
## Run all jobs
jh.run_jobs()
```

The `output_max_attempts` argument of the [JobHandler](classes/JobHandler.md) defines how many attempts are made to find the output file for a given job that is in FINISHED state. By default it is set to 5, in order to avoid delayed availablity of the output file in the underlying file system.

### FINISHED and SUCCESS trigger in the run_script
You can also set triggers in the run_script to indicate at which point in the job processing it should be considered as FINISHED and/or SUCCESS.

```python
from slurmy import JobHandler

## Set up the JobHandler
jh = JobHandler()
## Define the run script content
run_script = """
echo "hans"
@SLURMY.FINISHED
echo "horst"
@SLURMY.SUCCESS
"""
## Add a job
jh.add_job(run_script = run_script)
## Run all jobs
jh.run_jobs()
```

From a technical point, `@SLURMY.FINISHED` and `@SLURMY.SUCCESS` are substituted by temporary files, which are created at these points in the script. The FINISHED/SUCCESS evaluation is then checking if these files exist. The file name associated to `@SLURMY.SUCCESS` is also set as `output`, if it's not already specified as `add_job` argument.

## Custom evaluations for success, finished, and post-execution

You can define a custom finished condition by creating a dedicated class with \_\_call\_\_ defined. The function has to have exactly one argument, which is the config instance of the job. If `finished_func` is defined during add_job, the custom definition will be used instead of the default one during the finished evaluation.

This example uses the predefined [FinishedTrigger](utils/FinishedTrigger.md) class, which checks if the specified file exists on disk in order to evaluate whether if the job finished or not.

```python
from slurmy import JobHandler, FinishedTrigger

## Set up finished evaluation class
finished_file = '~/hans.txt'
ft = FinishedTrigger(finished_file)
## Set up the JobHandler
jh = JobHandler()
## Define the run script content
run_script = """
touch {}
""".format(finished_file)
## Add a job
jh.add_job(run_script = run_script, finished_func = ft)
## Run all jobs
jh.run_jobs()
```

This will actually do the same as the `@SLURM.FINISHED` example above.

In the same way as `finished_func`, you can also define `success_func`, to evaluate if a job is successful, or `post_func`, to define a post-processing which will be done locally after the job's success evaluation was done.

### Regarding class definitions

Due to technically reasons connected to the [snapshot feature](howto.md#snapshots), your custom class definition must be known to python on your machine. The best way to ensure that is to make the definition known to python via PYTHONPATH. In principle you can just use a local function definition instead of a callable class if you don't want to use the snapshot feature. However, it is highly recommended to make use of it.