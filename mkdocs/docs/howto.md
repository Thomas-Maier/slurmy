
## General Usage

You can just write a piece of python code that imports the required slurmy classes (e.g. [JobHandler](classes/JobHandler.md) and the backend class of your choice), defines jobs and calls the job submission. Job execution definitions can either be provided by already written batch shell scripts, or by defining the content of the shell script directly in your python code. For both cases, arguments that should be passed upon the execution to the scripts can also be specified.

<a name="slurmyconfig"></a>
## What you want to do before doing anything else

You can (and should) specify a slurmy config file, which defines your default configuration of relevant slurmy properties. In particular you can define which batch system backend you want to use and how it should be configured. This safes you from having to specify this every single time you want to use slurmy.

You just need to create a file `~/.slurmy` with this content (which you might want to modify):

```shell
bookkeeping = ~/.slurmy_bookkeeping
workdir = ./
backend = Slurm
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
jh.add_job(run_script = run_script_2, parent_tags = 'horst')
## Run all jobs
jh.run_jobs()
```

## Custom evaluations for success, finished, and post-execution

By default, the exitcode of the job (either taken from the local process or from the batch system bookkeeping) is taken to determine if it was successful or not. However, you can define a custom success condition by creating a dedicated class with \_\_call\_\_ defined. The function has to have exactly one argument, which is the config instance of the job. If `success_func` was defined during add_job, the custom definition will be used instead of the default one during the success evaluation.

This example uses the predefined [SuccessOutputFile](utils/SuccessOutputFile.md) class, which checks if the output associated to job exists on disk in order to evaluate whether if it succeeded or not.

```python
from slurmy import JobHandler, SuccessOutputFile

## Set up success evaluation class which checks if the job's output exists or not
sf = SuccessOutputFile()
## Set up the JobHandler
jh = JobHandler(success_func = sf)
## Define the run script content
run_script = """
touch ~/hans.txt
"""
## Add a job, specifying the output of the job.
##The success evaluation class can be specified for each job separately.
jh.add_job(run_script = run_script, output = '~/hans.txt', success_func = sf)
## Run all jobs
jh.run_jobs()
```

In the same way as `success_func`, you can also define `finished_func`, to evaluate if a job is finished, or `post_func`, to define a post-processing which will be done locally after the job's success evaluation was done.

### Regarding class definitions

Due to technically reasons connected to the [snapshot feature](howto.md#snapshots), your custom class definition must be known to python on your machine. The best way to ensure that is to make the definition known to python via PYTHONPATH. In principle you can just use a local function definition instead of a callable class if you don't want to use the snapshot feature. However, it is highly recommended to make use of it.