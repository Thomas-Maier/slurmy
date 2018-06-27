You can use the `slurmy` executable to start an interactive slurmy session, which allows to interact with past JobHandler sessions or start new ones.

Usage from `slurmy --help`:

```shell
usage: slurmy [-h] [-p PATH] [-c CONFIG] [-t] [--debug]

Slurmy interactive

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  Path to the base folder of an existing JobHandler
                        session. Directly loads the JobHandler as "jh".
  -c CONFIG, --config CONFIG
                        Path to a job configuration file.
  -t                    Switch to start in test mode.
  --debug               Run in debugging mode.
```

If you prefer to use python2 (not recommended), you can also run the `slurmy2` executable.

If no argument is passed to the slurmy executable, it tries to load the latest session according to the bookkeeping and load it as `jh`.

# Example usage

In general you can do everything in interactive slurmy that you can also do in python file which handles your job definition. On top of that you can easily inspect and manipulate an already existing [JobHandler](classes/JobHandler.md) session. Just executing `slurmy` will bring up the latest [JobHandler](classes/JobHandler.md) session:

```python
In [1]: jh
Out[1]: Azathoth_1530051215
```

Every [JobHandler](classes/JobHandler.md) has a member `jobs` which keeps track of all it's attached jobs:

```python
In [2]: jh.jobs
Out[2]: 
Job "hans": CONFIGURED
------------
CONFIGURED(1)
```

As you can see, the [JobHandler](classes/JobHandler.md) in this case has one job named "hans", which is in the CONFIGURED state. Every job is attached as property to [JobHandler](classes/JobHandler.md).jobs, which provides a direct handle to access them:

```python
In [3]: jh.jobs.hans
Out[3]: 
Job "hans"
Local: False
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/Azathoth_1530051215/scripts/hans
Status: CONFIGURED
```

Alternatively, jobs can be accessed directly by name via the [JobHandler](classes/JobHandler.md) itself:

```python
In [4]: jh['hans']
Out[4]: 
Job "hans"
Local: False
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/Azathoth_1530051215/scripts/hans
Status: CONFIGURED
```

[JobHandler](classes/JobHandler.md).jobs also has a `status_` property for every possible job status, which will print all jobs which currently are in this status:

```python
In [5]: jh.jobs.status_CONFIGURED
Job "hans": CONFIGURED

In [6]: jh.jobs.status_RUNNING


In [7]:
```

In this example, job "hans" is in CONFIGURED state so we can run the job submission (`run_jobs` for continuous submission until finished or `submit_jobs` for a single submission cycle):

```python
In [7]: jh.run_jobs()
Jobs processed (batch/local/all): (1/0/1)
     successful (batch/local/all): (0/0/0)
     failed (batch/local/all): (1/0/1)
Time spent: 5.4 s
```

(Note: the submission interval of `run_jobs` is set to 5 seconds by default)

The job "hans" is now in FAILED state:

```python
In [8]: jh.jobs
Out[8]: 
Job "hans": FAILURE
------------
FAILURE(1)
```

We can access the log file of the job directly via it's dedicated property (which opens the log with less), in order to find out what went wrong:

```python
In [9]: jh.jobs.hans.log
```

Usually, you probably want to fix our job configuration setup to fix a systematic problem in the job's run script creation. However, you can edit the run script directly:

```python
In [10]: jh.jobs.hans.edit_script()
```

If any of the jobs ended up in FAILED or CANCELLED state, they can be retried by passing `retry = True` to `run_jobs` or `submit_jobs`:

```python
In [11]: jh.run_jobs(retry = True)
Jobs processed (batch/local/all): (1/0/1)
     successful (batch/local/all): (1/0/1)
Time spent: 5.3 s
```

The job "hans" is now in SUCCESS state (from fixing the run script before retrying the job):

```python
In [12]: jh.jobs
Out[12]: 
Job "hans": SUCCESS
------------
SUCCESS(1)
```

While the job management should be handled by the [JobHandler](classes/JobHandler.md), you can also run job commands directly:

```python
In [13]: jh.jobs.hans.rerun()

In [14]: jh.jobs.hans.get_status()
Out[14]: <Status.SUCCESS: 3>
```

You should also run `jh.check_status()` to update the [JobHandler](classes/JobHandler.md) job bookkeeping:

```python
In [15]: jh.check_status()
Jobs (success/fail/all): (1/0/1)
```

However, it's likely that running jobs directly screws up the bookkeeping.

Finally, if you want to start from a clean slate you can reset the [JobHandler](classes/JobHandler.md) completely:

```python
In [16]: jh.reset()
In [17]: jh.run_jobs()
Jobs processed (batch/local/all): (0/1/1)
     successful (batch/local/all): (0/1/1)
Time spent: 5.4 s
```

In this case you actually might want to start again from the job configuration script that you wrote for your job submission.

Have a look at the [JobHandler](classes/JobHandler.md) and [Job](classes/Job.md) documentation to see what you execute in interactive slurmy.

# Job configuration file

The job definition file passed with `-c` is a convenient way to make job definitions. Inside the slurmy session, all necessary imports, like JobHandler and the backend classes, are already provided. This allows for skimmed down JobHandler setups that then can be further interacted with (you can omit import statements). As long as your definition file is "flat" (no encapsulated definitions), i.e. like the examples given in the [HowTo](howto.md) section, you can pass it to interactive slurmy.

# Interactive slurmy functions

The interactive slurmy session also defines a couple of functions.