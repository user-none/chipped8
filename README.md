# Chipped 8

Chipped 8 is a Chip-8 emulator written in Python. It is designed to have the
GUI decoupled from the core system allowing different GUI's to be used.

## Chip-8 Instruction Version

The XO-Chip (Octo) instruction set is supported. Which is a superset of
instructions and allows for Chip-8, Super Chip-8 1.0 to also be supported.

That said, there have been multiple [revisions /
versions](https://chip-8.github.io) of Chip-8 that are incompatible with each
other. Flags to handle differences in behavior are not currently supported.
Any Chip-8 and Super Chip-8 ROMs must be compatible with XO-Chip.

Super Chip-8 1.1 ROMs will mot likely not work due to the FX55 and FX65 not
incrementing I in that is unique to 1.1.

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
$ python -m venv c8env
$ source c8venv/bin/activate
$ cd chipped8
$ pip install .
$ chipped8 rom.ch8
```

Use `-e` with the `pip` step if installing for development where you will be able
to edit the source without running `pip` again.

Also, if testing new entry point, the following can be used:
`python -m chipped8.main_new_testing rom.ch8`

## Roms

Since Chip-8 wasn't a commercial game system everything running on it is
pretty much homebrew. There are a number of resources with interesting ch8
roms that you can play. This is a non-exhaustive list.

* [Test Rom](https://github.com/corax89/chip8-test-rom)
* [CHIP-8 Archive](https://johnearnest.github.io/chip8Archive/?sort=platform)
* [loktar00 Rom Collection](https://github.com/loktar00/chip8/tree/master/roms)

