# SLURMY - Special handLer for Universal Running of Multiple jobs, Yes!

Slurmy is a general batch submission module, which allows to define very general jobs to be run on batch system setups on linux computing clusters. Currently, only slurm is supported as backend, but further backends can easily be added. The definition of the job execution is done with a general shell execution script, as is used by most batch systems. In addition to the batch definition, jobs can also be dynamically executed locally, which allows for an arbitrary combination of batch and local jobs.

Please have a look at the [documentation page](https://thomas-maier.github.io/slurmy/) for more information.