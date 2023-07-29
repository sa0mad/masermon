# masermon udev
**masermon** is a tool to pull data from a maser over serial port and insert
into an InfluxDB database.
The udev library contains the example file **99-usb-serial.rule** which should
be moved into **/etc/udev/rules.d**. The acutal rules was used to map my serial
devices to **/dev/ttyUSBx** fitting my need.
