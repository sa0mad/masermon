# masermon systemd
**masermon** is a tool to pull data from a maser over serial port and insert
into an InfluxDB database.

The **systemd** library contains the example files which
should be linked into `/etc/systemd/system`. The acutal rules was used to map my
serial devices to `/dev/ttyUSBx` fitting my need.

To enable a systemd service such as `bme280.service`, do:
'cd /etc/systemd/system
ln -s /home/pi/maserjunk/masermon/systemd/bme280.service .
sudo systemctl daemon-reload
sudo systemctl enable bme280.service
sudo systemctl start bme280.service`
This should be done for all services you wish to operate. Please note that the
files should be edited for your need before starting. Editing a file requires
and additional `sudo systemctl daemon-reload` as you will be reminded to do.

Inspiration for this comes from [Sparkfun - How to Run a Raspberry Pi program on startup](https://learn.sparkfun.com/tutorials/how-to-run-a-raspberry-pi-program-on-startup#method-3-systemd). 

The devices mapped are these

* `/dev/ttyUSB4` HP5071A cesium clock over USB-RS232 adapter
* `/dev/ttyUSB5` DPM7885 pressure sensor over USB-RS232 adapter
* `/dev/ttyUSB6` VE Direct USB adapter
