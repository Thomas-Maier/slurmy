## Interactive Slurmy

You can use the slurmy executable to start an interactive slurmy session, which allows to interact with past JobHandler sessions or start new ones.

Arguments that can be passed to the executable:

**-p PATH**: Path to the base folder of a JobHandler session. Directly loads the JobHandler as "jh".

**-c CONFIG**: Path to a job definition file. More details, see below.

**--debug**: Run in debugging mode.

The job definition file passed with **-c** is a convenient way to make job definitions. Inside the slurmy session, all necessary imports, like JobHandler and the backend classes, are already provided. This allows for skimmed down JobHandler setups that then can be further interacted with.

**Example of a job definition file which can be passed to slurmy:** [examples/example_interactive_config.py](examples/example_interactive_config.py)

If no argument is passed to the slurmy executable, it tries to load the latest session according to the bookkeeping.

The interactive slurmy session also defines a couple of functions:

**list_sessions()**: List all past JobHandler sessions with some information. Sessions are kept track of in a json file, which is defined in ~/.slurmy. They are either defined by the full path to the base folder on disk, or by the name as given in the list.

**load(name)**: Load a JobHandler as given by the name in list_sessions().

**load_path(path)**: Load a JobHandler as given by the path to the base folder (relative or absolute).

**load_latest()**: Load the latest session according to the bookkeeping.