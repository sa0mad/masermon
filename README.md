# masermon
**masermon** is a tool to pull data from a maser over serial port and insert
into an InfluxDB database. It has  originally been designed for the EFOS-B
line of hydrogen masers, but intention  is to include other masers.
Support have been added for the HP5071A cesium clock and the DPM7885 absolute
pressure sensor.

`udev` contains an udev device mapping example as used for a setup, to
illustrate how USB devices can get static names for easing scripting.

`systemd` contains a few systemd service examples as used for a setup, to
illustrate how to autostart the logging upon boot/reboot but while waiting for
influxdb to be up. Having done the `udev` mappings, this can then have the
static configuration.
