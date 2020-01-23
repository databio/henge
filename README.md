# A Skeleton Python CLI 

This repository contains a skeleton that shows you how to create a python package that behaves as a command-line tool. If you install this repository with `pip`, you will then have access to a new shell command called `packagename`.

## Packagename

Install with: `pip install --user .`

Run with: `packagename -i INPUT -p PARAMETER`

See: `packagename --help` for details.

## Make it yours

Just copy all the files in this repository into a new repository and then edit them. You can edit these files to replace `packagename` everywhere with the name of the tool you want to create. Then, just make the function call whatever python code you need it to.

## Explanation

The creation of a command-line tool happens in `setup.py` in the lines that say:

```
entry_points={
    "console_scripts": [
        'packagename = packagename.packagename:main'
    ],
},    
```

Here `packagename = ...` is the command that will eventually be created; and
then `packagename.packagename` are 1) the name of the folder and then 2) the
name of the file that you want the command to run. Finally, `:main` says to run
the main function in that file.

### Logmuse

This package sets you up automatically to use the *logmuse* package, which gives
your tool parameters like `--verbosity` and `--logdev`, which change the
logging. You can use `_LOGGER.debug()` and `_LOGGER.info()`, and
`_LOGGER.warn()`, *etc*, to emit different classes of error messages. It's
already configured. You can read the logmuse documentation for more info.

