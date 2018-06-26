# Interactive Slurmy

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

The job definition file passed with `-c` is a convenient way to make job definitions. Inside the slurmy session, all necessary imports, like JobHandler and the backend classes, are already provided. This allows for skimmed down JobHandler setups that then can be further interacted with (you can omit import statements). As long as your definition file is "flat" (no encapsulated definitions), i.e. like the examples given in the [HowTo](howto.md) section, you can pass it to interactive slurmy

If no argument is passed to the slurmy executable, it tries to load the latest session according to the bookkeeping.

The interactive slurmy session also defines a couple of functions: