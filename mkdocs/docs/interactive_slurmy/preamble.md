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
Out[1]: MyAnalysis_1531405633
```

Every [JobHandler](classes/JobHandler.md) has a member `jobs` which keeps track of all it's attached jobs:

```python
In [2]: jh.jobs
Out[2]: 
Job "ttbar": CONFIGURED
Job "wjets": CONFIGURED
Job "ww": CONFIGURED
Job "data": CONFIGURED
------------
CONFIGURED(4)
```

As you can see, the [JobHandler](classes/JobHandler.md) in this case has four jobs named "data", "ttbar", "wjets", and "ww", which is in the CONFIGURED state. Every job is attached as property to [JobHandler](classes/JobHandler.md).jobs, which provides a direct handle to access them:

```python
In [3]: jh.jobs.ww
Out[3]: 
Job "ww"
Type: BATCH
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/MyAnalysis_1531405633/scripts/ww
Status: CONFIGURED
Tags: {'bkg', 'ww'}
```

Alternatively, jobs can be accessed directly by name via the [JobHandler](classes/JobHandler.md) itself:

```python
In [4]: jh['ww']
Out[4]: 
Job "ww"
Type: BATCH
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/MyAnalysis_1531405633/scripts/ww
Status: CONFIGURED
Tags: {'bkg', 'ww'}
```

[JobHandler](classes/JobHandler.md).jobs also has a `status_` property for every possible job status, which will print all jobs which currently are in this status:

```python
In [5]: jh.jobs.status_CONFIGURED
Job "wjets": CONFIGURED
Job "data": CONFIGURED
Job "ww": CONFIGURED
Job "ttbar": CONFIGURED

In [6]: jh.jobs.status_RUNNING


In [7]:
```

As you've seen above, the job "ww" (and "ttbar" and "wjets" for that matter) has a tag "bkg", which was attached to the job via the `tags` option of [JobHandler.add_job()](classes/JobHandler.md#add_job). You can get the printout for jobs only tagged with "bkg" by calling the [JobContainer.print()](classes/JobContainer.md#print) method:

```python
In [7]: jh.jobs.print(tags='bkg')
Job "wjets": CONFIGURED
Job "ww": CONFIGURED
Job "ttbar": CONFIGURED
------------
CONFIGURED(3)
```

In this example, all jobs are in the CONFIGURED state so we can run the job submission with [JobHandler.run_jobs()](classes/JobHandler.md#run_jobs):

```python
In [8]: jh.run_jobs()
all: 100%|██████████████████████████████████████████████████████████████| 4/4 [, S=3, F=1, C=0]
data: 100%|█████████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
bkg: 100%|██████████████████████████████████████████████████████████████| 3/3 [, S=2, F=1, C=0]
-ttbar: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-wjets: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-ww: 100%|██████████████████████████████████████████████████████████████| 1/1 [, S=0, F=1, C=0]

Jobs processed (batch/local/all): (4/0/4)
     successful (batch/local/all): (3/0/3)
     failed (batch/local/all): (1/0/1)
Time spent: 12.4 s
```

You can see that this produces two different printouts. During the processing you'll get progress bars which indicate how many jobs are completed. On the very right of these progess bars you can also see how many jobs ended up in the SUCCESS(S), FAILED(F), or CANCELLED(C) state. You can also see that for each tag that is introduced with [JobHandler.add_job()](classes/JobHandler.md#add_job) one progress bar is displayed, which keeps track of the jobs assigned with this tag. Slurmy will also evaluate the tag hierarchy dependent on how tags were assigned to jobs and order them accordingly in this printout. In this example, each job has it's own name as tag and "ww", "ttbar", and "wjets" have "bkg" as an additional tag.

As you can see from the printout above, job "ww" ended up in FAILED state.

```python
In [9]: jh.jobs.ww
Out[9]: 
Job "ww"
Type: BATCH
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/MyAnalysis_1531405633/scripts/ww
Status: FAILED
Tags: {'bkg', 'ww'}
```

We can access the log file of the job directly with [Job.log](classes/Job.md#log) (which opens the log file with `less`), in order to find out what went wrong:

```python
In [10]: jh.jobs.ww.log
```

Usually, you probably want to fix your job configuration setup to fix a systematic problem in the job's run script creation. However, you can edit the run script directly:

```python
In [11]: jh.jobs.ww.edit_script()
```

If any of the jobs ended up in FAILED or CANCELLED state, they can be retried by passing `retry = True` to `run_jobs`:

```python
In [12]: jh.run_jobs(retry = True)
all: 100%|██████████████████████████████████████████████████████████████| 4/4 [, S=4, F=0, C=0]
data: 100%|█████████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
bkg: 100%|██████████████████████████████████████████████████████████████| 3/3 [, S=3, F=0, C=0]
-ttbar: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-wjets: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-ww: 100%|██████████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]

Jobs processed (batch/local/all): (4/0/4)
     successful (batch/local/all): (4/0/4)
Time spent: 2.5 s
```

The job "ww" is now in SUCCESS state (from fixing the run script before retrying the job):

```python
In [13]: jh.jobs.ww
Out[13]: 
Job "ww"
Type: BATCH
Backend: Slurm
Script: /home/t/Thomas.Maier/testSlurmy/MyAnalysis_1531405633/scripts/ww
Status: SUCCESS
Tags: {'bkg', 'ww'}
```

Finally, if you want to start from a clean slate you can reset the [JobHandler](classes/JobHandler.md) completely:

```python
In [14]: jh.reset()
In [15]: jh.run_jobs()
all: 100%|██████████████████████████████████████████████████████████████| 4/4 [, S=4, F=0, C=0]
data: 100%|█████████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
bkg: 100%|██████████████████████████████████████████████████████████████| 3/3 [, S=3, F=0, C=0]
-ttbar: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-wjets: 100%|███████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]
-ww: 100%|██████████████████████████████████████████████████████████████| 1/1 [, S=1, F=0, C=0]

Jobs processed (batch/local/all): (4/0/4)
     successful (batch/local/all): (4/0/4)
Time spent: 11.3 s
```

In this case you actually might want to start again from the job configuration script that you wrote for your job submission.

Have a look at the [JobHandler](classes/JobHandler.md) and [Job](classes/Job.md) documentation to see what you can execute in interactive slurmy.

# Job configuration file

The job definition file passed with `-c` is a convenient way to make job definitions. Inside the slurmy session, all necessary imports, like JobHandler and the backend classes, are already provided. This allows for skimmed down JobHandler setups that then can be further interacted with (you can omit import statements). As long as your definition file is "flat" (no encapsulated definitions), i.e. like the examples given in the [HowTo](howto.md) section, you can pass it to interactive slurmy.

# Interactive slurmy functions

The interactive slurmy session also defines a couple of functions.