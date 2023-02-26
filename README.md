# KiCad Auto Silkscreen Placer

**Compatibility:** KiCad 7.0. *Not tested with KiCad 6.0.*

## Plugin presentation

This KiCad plugin automatically computes positions for all silkscreen reference designators and value that are free of overlap with other PCB elements (footprints including their reference designators, solder mask, vias, PTH/NPTH holes, etc.).

<!-- ![](./sample_output.png) -->

It is intended to be used after laying out and routing a board to place most of the designators in an adequate position. Some manual work might still be required to improve the silkscreen, but this plugin will save a lot of time over doing it entirely manually.

## Install instructions

**Warning:** this plugin is under active development, but it is in working state.

To install the plugin from GitHub:
1. Clone/download this repository and extract it to your KiCad plugin folder. You can find it by opening the PCB editor, and using "Tools" > "Externals Plugins" > "Open Plugin Directory".
2. Refresh the plugins by restarting the PCB editor or using "Tools" > "Externals Plugins" > "Refresh Plugins".

## Usage instructions

**It is recommended to back-up the PCB file before using this plugin.** The changes made by executing the plugin can be reverted by pressing "Undo" (Ctrl+Z).

Use the button in the toolbar to open the plugin window and configure its parameters.

The processing time of the plugin depend on the complexity of the PCB and the value of the parameters. It can take multiple minutes.

## License

This plugin is published under MIT license.
