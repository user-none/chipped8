# Chipped 8

Chipped 8 is a Chip-8 emulator written in Python. It is designed to have the
GUI decoupled from the core system allowing different GUI's to be used.

## Chip-8 Instruction Version

There have been multiple [revisions / versions](https://chip-8.github.io) of
Chip-8 that introduce incompatibilities with each other. Most Chip-8 versions
are supported via specifying the target platform when starting the application.

Choices are:

- originalChip8
- hybridVIP
- modernChip8
- chip48
- superchip1
- superchip
- xochip

The default is originalChip8. The platform specifies behavior flags as
defined by the [Chip-8 Research Facility](https://github.com/chip-8/chip-8-database).

## GUI

The GUI is a work in progress and uses Qt. It supports basic features such as
emulation automatically pausing if focus is lost and few key controls.

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


## Rewind

Basic rewind is supported for 30 seconds.

## Install and Run

```
$ python -m venv c8venv
$ source c8venv/bin/activate
$ cd chipped8
$ pip install .
$ chipped8 rom.ch8
```

Use `-e` with the `pip` step if installing for development where you will be able
to edit the source without running `pip` again.

Also, if testing new entry point, the following can be used:
`python -m chipped8.main_new_testing rom.ch8`

