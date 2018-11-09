# SLURMY - Special handLer for Universal Running of Multiple jobs, Yes!

Slurmy is a general batch submission module, which allows to define very general jobs to be run on batch system setups on linux computing clusters. Currently, only Slurm and HTCondor are supported as backends, but further backends can easily be added. The definition of the job execution is done with a general shell execution script, as is used by most batch systems. In addition to the batch definition, jobs can also be dynamically executed locally, which allows for an arbitrary combination of batch and local jobs.

## Installation

First off, it is very much recommended to use slurmy in python3. While it is compatible with python2, some features only work (properly) in python3. You can either install slurmy using pip or directly check out the git repository.

### pip

Most likely you won't have root privileges on your machine, so you have to make a user pip installation:

```shell
pip install --user slurmy
```
Depending on your setup `pip` points to the python2 or python3 pip executable. In order to ensure that you're installing slurmy for python3 you can be more explicit:
```shell
pip3 install --user slurmy
```

This will install the slurmy module in `~/.local/lib/pythonX.Y/site-packages/` (`X.Y` indicates the version of your python installation) and the slurmy executables in `~/.local/bin/`. In order to ensure that python properly finds the module and you can run the executables, you should add the respective paths to `PYTHONPATH` and `PATH`:

```shell
MYPYTHONVERSION=python$(python3 -c "from sys import version_info; print('{}.{}'.format(version_info.major, version_info.minor))")
export PYTHONPATH=~/.local/lib/$MYPYTHONVERSION/site-packages:$PYTHONPATH
export PATH=~/.local/bin:$PATH
```

### github

Clone the latest stable tag or (if you're brave) master branch locally:

```shell
git clone https://github.com/Thomas-Maier/slurmy.git
LATESTTAG=$(git describe --abbrev=0 --tags)
git co $LATESTTAG
```

Make sure to add the respository folder to `PYTHONPATH` and the `bin/` folder to `PATH`':

```shell
## Assuming that we are in the repository folder now
export PYTHONPATH=$PWD:$PYTHONPATH
export PATH=$PWD/bin:$PATH
```

Also, take a look at the [slurmy config setup](howto.md#slurmyconfig).
