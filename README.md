# SLURMY - Special handLer for Universal Running of Multiple jobs, Yes!

Slurmy is a general batch submission module, which allows to define very general jobs to be run on batch system setups on linux computing clusters. Currently, only slurm is supported as backend, but further backends can easily be added. The definition of the job execution is done with a general shell execution script, as is used by most batch systems. In addition to the batch definition, jobs can also be dynamically executed locally, which allows for an arbitrary combination of batch and local jobs.

Currently, slurmy is only compatible with python 3. This is due to the highly more robust subprocess handling and other smaller features. In the future, I'll make in attempt to work with python 2 as well but that would be to the detriment of some of said feature (when used in python 2).

NOTE: This readme temporarily will contain some instruction on how to use slurmy. In the future a proper documentation will be added.

## Recommended Setup

Clone the latest stable tag or master branch locally:

git clone https://github.com/TomVanNom/slurmy.git

Make sure to add the directory in which you cloned slurmy to PYTHONPATH, and the slurmy folder to PATH:

export PYTHONPATH=$PWD:$PYTHONPATH

export PATH=$PWD/slurmy:$PATH

This will make python aware of the slurmy module and you'll be able to execute the slurmy executable.

## General Usage

You can just write a piece of python code that imports the needed slurmy classes (e.g. JobHandler and the backend class of your choice), defines jobs and calls the job submission. Job execution definitions can either be provided by already written batch shell scripts, or by defining the content of the shell script directly in your python code. For both cases, arguments that should be passed upon the execution to the scripts can also be specified.

**Example of simple slurm jobs definition:** [examples/example_slurm_simple.py](examples/example_slurm_simple.py)

You can also make use of the interactive slurmy functionality to load a job configuration, more on that later.

## Slurmy Configuration File

Since you'll most likely have only one batch system with some required configurations, it's possible to set up a general configuration file which specifies the backend to be used and it's configuration. If you do so, no backend configuration has to be done when making the job definition. You can also define some general slurmy configurations in this file.

**Template of slurmy config file:** [examples/slurmy_config](examples/slurmy_config)

Copy this file into your home directory (name must be ".slurmy") and set configurations according to your requirements:

cp examples/slurmy_config ~/.slurmy

NOTE: All further examples assume that ~/.slurmy exists, which properly defines the backend and backend configurations.

## Chaining Jobs with Tags

Jobs can be connected by adding tags and parent tags to them. Jobs with parent tags X,Y, and Z will only be executed if all jobs that have the tags X, Y, or Z have successfully finished.

**Example of job chaining with tags:** [examples/example_chain.py](examples/example_chain.py)

## Custom Success Conditions and Variable Substitution

By default, the exitcode of the job (either taken from the local process or from the batch system bookkeeping) is taken to determine if it was successful or not. However, you can define a custom success condition by creating a dedicated class with \_\_call\_\_ defined. The function has to have exactly one argument, which is the config instance of the job. If success_func was defined during add_job, the custom definition will be used instead of the default one during the success evaluation.

**Example of success_func usage:** [examples/example_success_func.py](examples/example_success_func.py)

Due to technically reasons connected to the snapshot feature (see below), your custom class definition must be known to python on your machine. The best way to ensure that is to make the definition known to python via PYTHONPATH. In principle you can just use a local function definition instead of a callable class if you don't want to use the snapshot feature. However, it is highly recommended to make use of it.

The example uses SuccessOutputFile as defined in tools/utils.py. It also introduces a feature of slurmy, that allows to use the configuration of the JobHandler inside the shell script and some arguments of add_job (currently only "output"). This is done by some simple string parsing and substitution routine of any variable of the JobHandlerConfig. For now have a look at [tools/JobHandler.py](tools/JobHandler.py) to see what can be used (all variables that don't start with "_").

## Snapshots

By default, slurmy will make snapshots of your JobHandler session, which allows to load your job submission session at a later time (in interactive slurmy). You can deactivate this feature by passing "do_snaphot = False" to the JobHandler construction. If deactivated, the submission session can't be properly loaded in interactive slurmy anymore.

## JobHandler Options

Arguments that can be passed to the JobHandler construction:

**name** (default: None): Name used for the session. This defines the name of the base folder, where logs, submission scripts, etc. are stored.

**backend** (default: None): Default backend to be used.

**work_dir** (default: ""): Path to the work directory where the base folder is to be placed.

**local_max** (default: 0): Maximum number of concurrent local processes to be run. Setting this to a value greater than 0 will trigger the usage of local processes, otherwise only batch jobs will be submitted.

**success_func** (default: None): Default success definition to be used.

**max_retries** (default: 0): Maximum number of retries that will be attempted.

**theme** (default: Lovecraft): Theme that is used by the name generator to name individual jobs and the base folder name. Priority is given to the "name" argument. Themes can be used as given by the Theme enums in tools/defs.py. If Boring is used, job names are simply the base folder name with an incrementing integer.

**run_max** (default: None): Maximum number of jobs that are submitted concurrently. Sometimes needed to not overload batch systems.

**do_snapshot** (default: True): Switch for snapshot deactivation.

**description** (default: None): Description of the JobHandler. For bookkeeping purposes.

## Arguments for add_jobs

Arguments that can be passed to the add_jobs function of JobHandler:

**backend** (default: None): Backend to be used by the job.

**run_script** (default: None): The shell script that defines the job execution. Can either be the script as one string block, or the name of a script on disk.

**run_args** (default: None): Run arguments that should be passed to the shell script. Can be either a string or a list of strings. It is recommended to simply pass a string that reflects the same sequence that you would also write in a shell line command.

**success_func** (default: None): Success definition to be used by the job.

**max_retries** (default: None): Maximum number of retries that will be attempted by the job.

**output** (default: None): User defined output of the job. Can be anything, since it's not used by the job.

**tags** (default: None): Tags that should be attached to the job. Can be a string or a list of strings.

**parent_tags** (default: None): Parent tags that should be attached to the job. Can be a string or a list of strings.

## Interactive Slurmy

You can use the slurmy executable to start an interactive slurmy session, which allows to interact with past JobHandler sessions or start new ones.

Arguments that can be passed to the executable:

**-p PATH**: Path to the base folder of a JobHandler session. Directly loads the JobHandler as "jh".

**-c CONFIG**: Path to a job definition file. More details, see below.

**--debug**: Run in debugging mode.

The job definition file passed with **-c** is a convenient way to make job definitions. Inside the slurmy session, all necessary imports, like JobHandler and the backend classes, are already provided. This allows for skimmed down JobHandler setups that then can be further interacted with.

**Example of a job definition file which can be passed to slurmy:** [examples/example_interactive_config.py](examples/example_interactive_config.py)

The interactive slurmy session also defines a couple of functions:

**list_sessions()**: List all past JobHandler sessions with some information. Sessions are kept track of in a json file, which is defined in ~/.slurmy. They are either defined by the full path to the base folder on disk, or by the name as given in the list.

**load(name)**: Load a JobHandler as given by the name in list_sessions().

**load_path(path)**: Load a JobHandler as given by the path to the base folder (relative or absolute).
