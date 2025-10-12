# Chipped 8

Chipped 8 is a Chip-8 emulator written in Python. It is designed to have the
GUI decoupled from the core system allowing different GUI's to be used.

## Chip-8 Instruction Version

There have been multiple [revisions / versions](https://chip-8.github.io) of
Chip-8 that introduce incompatibilities with each other. Most Chip-8 versions
are supported via specifying the target platform when starting the application.

Choices are:

- originalChip8
- hybridVIP [^1]
- modernChip8
- chip48
- superchip1
- superchip
- xochip

The default is originalChip8. The platform specifies behavior flags as
defined by the [Chip-8 Research Facility](https://github.com/chip-8/chip-8-database).

## GUI

The GUI is a work in progress and uses Qt.

Some of the features currently supported

- Auto pause if focus is lost
- A variety of shaders
- Color presets and customization

### Keyboard Mapping

In order to make the Chip-8 0-1 and A-F keys easier to use on a keyboard the
following mapping is used.

```
Chip-8  | Keyboard
--------|---------
1 2 3 C | 1 2 3 4
4 5 6 D | Q W E R
7 8 9 E | A S D F
A 0 B F | Z X C V
```

Emulator Controls

Key        | Modifier | description
---------- | -------- | -----------
`P`        |          | Pause and unpause emulation.
Left arrow |          | Rewind 1 frame
Left arrow | Shift    | Rewind 60 frames (1 second)
`~`        |          | Show / hide metadata overlay


### Rewind

Basic rewind is supported for 30 seconds.


### Metadata

ROM metadata is automatically downloaded from the [CHIP-8
database](https://github.com/chip-8/chip-8-database). The metadata is used to
auto select a number of parameters such as platform and tickrate on detected
ROMs. A selection of relevant metadata can be displayed as an overly.

## Interpreters

Multiple interpreters are supported.

1. Pure: `pure`. A pure interpreter that uses a decode 
2. Cached: `cachedo`. A Build-Then-Execute interpreter that uses class objects for instruction caching
3. Cached: `cachedolp`. A Build-Then-Execute interpreter that uses captured lambdas for instruction caching
3. Cached: `cachedolh`. An Execute-While-Building instruction that uses captured lambdas for instruction caching

The different interpreters are provided mainly to understand and test the differences between
various interpreter designs. None is better then another with chip-8 due to how few cycles take place
when executing instructions. Performance difference is overall negligible for all practical use.

The pure interpreter is the default but the other interpreters can be chosen as
a command line option or via the Interpreter menu in the GUI.

There are a few special cases where a given design provides better performance than others:

* `cachedolh` is faster when dealing with self modifying code than `cachedo` and `cachedlp`
  The Build-Then-Execute model is wasteful because blocks of instructions will be built and
  not fully executed due to self modification needing to reset the cache. Heavily self modifying
  code can have many instances where a multiple instructions are built into a block only to have
  a few run.
* The `pure` CPU in theory should be slower than the caching ones. However, it is the fastest in
  all situations.

The different interpreters are available mainly as an exercise in understanding different
designs. The execution of a ROM is identical across all of them.

## Install and Run

```
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install .
$ chipped8 rom.ch8
```

Use `-e` with the `pip` step if installing for development where you will be able
to edit the source without running `pip` again.

Alternatively, you can run without installing using the following.

```
$ python -m chipped8.main rom.ch8
```

### Standalone package

A standalone package can be built using PyInstaller. The package created will
include Python and all dependencies. Allowing distribution to other systems
without first needing to first install Python or application dependencies. It
is a fully standalone package.

A venv with all dependencies installed is required for PyInstaller
to create a standalone package. Create the environment and build the
package using the following.

```
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install .
$ pip install pyinstaller
$ pyinstaller pyinstaller/chipped8.spec
```

The package will be located in the `dist` directory.

Cross compiling is not supported by PyInstaller. The package created will
be for the OS you are building the package with. A GitHub workflow for creating
and uploading standalone packages as artifacts for macOS, Linux, and Windows
can be found in the `.github` directory.

## Unit Tests

Automated tests can be run using `pytest`. The opcode tests will run using all
interpreters. Tests are not comprehensive and a number of opcodes, mainly drawing,
do not have tests.

---

[^1]: 0NNN machine instructions are not supported
