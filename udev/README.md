# masermon udev
**masermon** is a tool to pull data from a maser over serial port and insert
into an InfluxDB database.

The **udev** library contains the example file `99-usb-serial.rule` which
should be moved into `/etc/udev/rules.d`. The acutal rules was used to map my
serial devices to `/dev/ttyUSBx` fitting my need.

Handy reference to udev hacking is [Writing udev rules](http://www.reactivated.net/writing_udev_rules.html), with some handy tips from [Stack Exchange - How to bind USB devices under a static name](https://unix.stackexchange.com/questions/66901/how-to-bind-usb-device-under-a-static-name). Since these are useful but dated, look at the example for an updated format that seems to work for inspiration.

The devices mapped are these

* `/dev/ttyUSB4` HP5071A cesium clock over USB-RS232 adapter
* `/dev/ttyUSB5` DPM7885 pressure sensor over USB-RS232 adapter
* `/dev/ttyUSB6` VE Direct USB adapter
