# SLURMY - Special handLer for Universal Running of Multiple jobs, Yes!

Slurmy is a general batch submission module, which allows to define very general jobs to be run on batch system setups on linux computing clusters. Currently, only slurm is supported as backend, but further backends can easily be added. The definition of the job execution is done with a general shell execution script, as is used by most batch systems. In addition to the batch definition, jobs can also be dynamically executed locally, which allows for an arbitrary combination of batch and local jobs.

NOTE: This readme temporarily will contain some instruction on how to use slurmy. In the future a proper documentation will be added.

## Recommended Setup

Clone the latest stable tag or master branch locally:

git clone https://github.com/TomVanNom/slurmy.git

Make sure to add the directory in which you cloned slurmy to PYTHONPATH, as well as the slurmy folder:

export PYTHONPATH=$PWD:$PWD/slurmy:$PYTHONPATH

This will make python aware of the slurmy module and you'll be able to execute the slurmy executable.

## General usage

You can just write a piece of python code that imports the needed slurmy classes, like JobHandler and the backend class of your choice, defines jobs and calls the job submission. Job execution definitions can either be provided by already written batch shell scripts, or by defining the content of the shell script directly in your python code. For both cases, arguments that should be passed upon the execution to the scripts can also be specified.

*Example of simple slurm jobs definition:* examples/example_slurm_simple.py

You can also make use of the interactive slurmy functionality to load a job configuration, more on that later.

Since you'll most likely have only one batch system with some required configurations, it's possible to set up a general configuration file which specifies the backend to be used and it's configuration. If you do so, no backend configuration has to be done when making the job definition. You can also define some general slurmy configurations in this file.

Template of slurmy config file: examples/slurmy_config

Copy this file into your home directory (name must be ".slurmy") and set configurations according to your requirements:

cp examples/slurmy_config ~/.slurmy

NOTE: All further examples assume that ~/.slurmy exists, which properly defines the backend and backend configurations.

Jobs can be connected by adding tags and parent tags to them. Jobs with parent tags X,Y, and Z will only be executed if all jobs that have the tags X, Y, or Z have successfully finished.

Example of job chaining with tags: examples/example_chain.py

By default, the exitcode of the job (either taken from the local process or from the batch system bookkeeping) is taken to determine if it was successful or not. However, you can define a custom success evaluation by creating a dedicated class with __call__ defined. The function has to have exactly one argument, which is the config instance of the job. During the evaluation whether the job was successful or not, if success_func was defined during add_job, the custom definition will be used instead of the default one.

Example of success_func usage: examples/example_success_func.py

The example uses SuccessOutputFile as defined in tools/utils.py. It also introduces a feature of slurmy, that allows to use the configuration of the jobhandler inside the shell script and some arguments of add_job (currently "output"). This is done by some simple string parsing and substitution routine of any variable of the JobHandlerConfig. For now have a look tools/JobHandler.py to see what can be used (all variables that don't start with "_").

## Interactive Slurmy

