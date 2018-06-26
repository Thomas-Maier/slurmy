# SLURMY - Special handLer for Universal Running of Multiple jobs, Yes!

Slurmy is a general batch submission module, which allows to define very general jobs to be run on batch system setups on linux computing clusters. Currently, only slurm is supported as backend, but further backends can easily be added. The definition of the job execution is done with a general shell execution script, as is used by most batch systems. In addition to the batch definition, jobs can also be dynamically executed locally, which allows for an arbitrary combination of batch and local jobs.

## Recommended Setup

Clone the latest stable tag or master branch locally:

git clone https://github.com/Thomas-Maier/slurmy.git

Make sure to add the directory in which you cloned slurmy to PYTHONPATH, and the slurmy folder to PATH:

export PYTHONPATH=$PWD:$PYTHONPATH

export PATH=$PWD/slurmy:$PATH

This will make python aware of the slurmy module and you'll be able to execute the slurmy executable.

Also, take a look at the [slurmy config setup](howto.md#slurmyconfig).