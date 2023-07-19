#!/usr/bin/env python3

import serial
import time
import sys
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError
import datetime
import json
import traceback
import click
import binascii
import re
import logging
# For Environ+ module
from bme280 import BME280
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
# For VE Direct module
import argparse, os
from vedirect import Vedirect

efosb_channels = [
    { "chan": 0,    "name": "InputA_U",       "signed": -128,   "scale": 0.230,   "offset": 0    },
    { "chan": 1,    "name": "InputA_I",       "signed": -128,   "scale": 0.096,   "offset": 0    },
    { "chan": 2,    "name": "InputB_U",       "signed": -128,   "scale": 0.230,   "offset": 0    },
    { "chan": 3,    "name": "InputB_I",       "signed": -128,   "scale": 0.096,   "offset": 0    },
    { "chan": 4,    "name": "Temp",           "signed": -128,   "scale": 0.960,   "offset": -1.1 },
    { "chan": 5,    "name": "Hpress_set",     "signed": -128,   "scale": 0.096,   "offset": 0    },
    { "chan": 6,    "name": "Hpress_read",    "signed": -128,   "scale": 0.096,   "offset": 0    },
    { "chan": 7,    "name": "Palladium_heat", "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 8,    "name": "LO_heat",        "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 9,    "name": "UO_heat",        "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 10,   "name": "Dalle_heat",     "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 11,   "name": "LI_heat",        "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 12,   "name": "UI_heat",        "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 13,   "name": "Cavity_heat",    "signed": -128,   "scale": 0.192,   "offset": 0    },
    { "chan": 14,   "name": "Temp_cavity",    "signed": -128,   "scale": 0.010,   "offset": 0    },
    { "chan": 15,   "name": "Temp_ambient",   "signed": -128,   "scale": 0.096,   "offset": 26   },
    { "chan": 16,   "name": "Cavity_var",     "signed": -128,   "scale": 0.096,   "offset": 0    },
    { "chan": 17,   "name": "C_field",        "signed": -128,   "scale": 1.920e-6,"offset": 0    },
    { "chan": 18,   "name": "int_N2_HT_U",    "signed": -128,   "scale": 0.048e+3,"offset": 0    },
    { "chan": 19,   "name": "int_N2_HT_I",    "signed": -128,   "scale": 19.00e-6,"offset": 0    },
    { "chan": 20,   "name": "int_N1_HT_U",    "signed": -128,   "scale": 0.048e+3,"offset": 0    },
    { "chan": 21,   "name": "int_N1_HT_I",    "signed": -128,   "scale": 19.00e-6,"offset": 0    },
    { "chan": 22,   "name": "ext_HT_U",       "signed": -128,   "scale": 0.048e+3,"offset": 0    },
    { "chan": 23,   "name": "ext_HT_I",       "signed": -128,   "scale": 19.00e-6,"offset": 0    },
    { "chan": 24,   "name": "RF_U",           "signed": -128,   "scale": 0.298,   "offset": 0    },
    { "chan": 25,   "name": "RF_I",           "signed": -128,   "scale": 0.010,   "offset": 0    },
    { "chan": 26,   "name": "p24V",           "signed": -128,   "scale": 0.240,   "offset": 0    },
    { "chan": 27,   "name": "p15V1",          "signed": -128,   "scale": 0.148,   "offset": 0    },
    { "chan": 28,   "name": "n15V1",          "signed": -128,   "scale": 0.148,   "offset": 0    },
    { "chan": 29,   "name": "p5V",            "signed": -128,   "scale": 0.148,   "offset": 0    },
    { "chan": 30,   "name": "p15V2",          "signed": -128,   "scale": 0.148,   "offset": 0    },
    { "chan": 31,   "name": "n15V2",          "signed": -128,   "scale": 0.148,   "offset": 0    },
    { "chan": 32,   "name": "OCXO",           "signed": 0,      "scale": 0.078,   "offset": 0    },
    { "chan": 33,   "name": "Ampl5.7k",       "signed": 0,      "scale": 0.078,   "offset": 0    },
    { "chan": 34,   "name": "Lock",           "signed": 0,      "scale": 1.000,   "offset": 0    },
]

def is_number(s):
    if s is None:
        return False
    if s.isnumeric():
        return True
    r = re.fullmatch('[+-]?([0-9]+)?[.]?[0-9]+([eE]([0-9]+))?',s)
    if r:
        return True
    return False

#with open('EFOS14.json') as f:
#    s = f.read()
#    channels = json.loads(s)

def efosb_poll_chan(ser, chan):
    cmd = "D%02d" % chan
    for i in range(0, 5):
        buf = b''
        try:
            for c in cmd:
                ser.write(c.encode())
                buf += ser.read()
            s = ser.read(size=4)
            buf += b'[' + s + b']'
            if s.endswith((b'\r', b'\n')):
                if len(s) == 4:
                    r = int(s, 16)
                    return (r, False)
                else:
                    print("Timeout")
            else:
                print("ERROR: malformed response", s)
        except:
            print("%s Channel %s Line Noise: %s" % (datetime.datetime.utcnow().isoformat(), chan, s))
            print("Trace:")
            print(buf)
            traceback.print_exc()
            time.sleep(0.01)
    return (-1, True)

def efosb_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE, BAUDRATE, LOGRATE):
    with serial.Serial(SERIALDEVICE, BAUDRATE, timeout=2) as ser:
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)
        fields = {}
        s = ''
        print("Syncing ...")
        while len(s) < 10:
            ser.write('F'.encode())
            s = ser.read(size=10)
            if len(s) < 10:
                print(s)
        print("Synthesizer f:", s.decode('ascii').strip())
        while True:
            timestamp = datetime.datetime.utcnow().isoformat()
            for channel in efosb_channels:
                val, err = efosb_poll_chan(ser, channel['chan'])
                if not err:
                    fields[channel['name']] = (val + channel['signed']) * channel['scale'] + channel['offset']
            json_body = [
                {
                    "measurement": MASERID,
                    "tags": {
                        "masetype": "EFOS-B",
                        "maser": MASERID
                     },
                    "time": timestamp,
                    "fields": fields
                }
            ]
            client.write_points(json_body)
            time.sleep(LOGRATE)

def vch1006_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE, BAUDRATE, LOGRATE):
    with serial.Serial(SERIALDEVICE, BAUDRATE, timeout=2) as ser:
       print("Test connection")
       ser.write(b'\x01')
       ser.write(b'\x41')
       ser.write(b'\x00')
       ser.write(b'\x00')
       ser.write(b'\x00')
       buf = ser.read(189)
       s = binascii.hexlify(bytearray(buf))
       print(s)

def scpi_write(SER, STR):
    SER.write(str.encode(STR+"\r\n"))
    s = SER.readline()

def scpi_read_line(SER):
    s = SER.readline()
    return s.decode("utf-8").rstrip()

def scpi_read_string(SER):
    s = scpi_read_line(SER)
    return re.sub(r'"', '', s)

def scpi_read_int(SER):
    s = scpi_read_line(SER)
    return int(s)

def scpi_read_intvec(SER):
    s = scpi_read_line(SER)
    return [int(x) for x in s.split(',')]

def scpi_read_float(SER):
    s = scpi_read_line(SER)
    return float(s)

def scpi_read_floatvec(SER):
    s = scpi_read_line(SER)
    return [float(x) for x in s.split(',')]
       
def hp5071a_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE, BAUDRATE, LOGRATE):
    with serial.Serial(SERIALDEVICE, BAUDRATE, bytesize=8, parity='N', stopbits=1, xonxoff=1, timeout=2) as ser:
        #client = InfluxDBClient(host='localhost', port=8086)
        #client = InfluxDBClient(host='labpi.rubidium.se', port=8086, ssl=True, ssl_verify=True)
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)
        # Start up and get Identity
        scpi_write(ser, "")
        scpi_write(ser, "*IDN?")
        s = scpi_read_line(ser)
        # Extract serial number from *IDN? string
        snr = int(re.split(r'[\,]+', s)[3])
        while True:
            timestamp = datetime.datetime.utcnow().isoformat()
            scpi_write(ser, "PTIM:MJD?")
            mjd = scpi_read_int(ser)
            scpi_write(ser, "PTIM?")
            ssplit = scpi_read_intvec(ser)
            hour = ssplit[0]
            min = ssplit[1]
            sec = ssplit[2]
            scpi_write(ser, "DIAG:CBTSerial?")
            CBTID = scpi_read_string(ser)
            scpi_write(ser, "DIAG:STAT?")
            CONT = scpi_read_string(ser)
            scpi_write(ser, "DIAG:CURR:BEAM?")
            CURR_BEAM = scpi_read_float(ser)
            scpi_write(ser, "DIAG:CURR:CField?")
            CURR_CFIELD = scpi_read_float(ser)
            scpi_write(ser, "DIAG:CURR:PUMP?")
            CURR_PUMP = scpi_read_float(ser)
            scpi_write(ser, "DIAG:GAIN?")
            GAIN = scpi_read_float(ser)
            scpi_write(ser, "DIAG:RFAMplitude?")
            RF_AMP = scpi_read_floatvec(ser)
            scpi_write(ser, "DIAG:TEMP?")
            TEMP = scpi_read_float(ser)
            scpi_write(ser, "DIAG:VOLT:COVen?")
            COVEN = scpi_read_float(ser)
            scpi_write(ser, "DIAG:VOLT:EMUL?")
            EMUL = scpi_read_float(ser)
            scpi_write(ser, "DIAG:VOLT:HWIonizer?")
            HWI = scpi_read_float(ser)
            scpi_write(ser, "DIAG:VOLT:MSPec?")
            MSP = scpi_read_float(ser)
            scpi_write(ser, "DIAG:VOLT:PLLoop?")
            PLL = scpi_read_floatvec(ser)
            PLL9_2 = PLL[0]
            PLL640 = PLL[1]
            PLL87  = PLL[2]
            PLL9   = PLL[3]
            scpi_write(ser, "DIAG:VOLT:SUPPly?")
            SUPP = scpi_read_floatvec(ser)
            VP5V = SUPP[0]
            VP12V = SUPP[1]
            VN12V = SUPP[2]
            scpi_write(ser, "DIAG:STAT:SUPPly?")
            SUPP = scpi_read_string(ser)
            json_body = [
                {
                "measurement": MASERID,
                "tags": {
                    "masertype": "HP5071A",
                    "maser": snr,
                    "tube": CBTID
                },
                "time": timestamp,
                "fields": {
                    "Supply": SUPP,
                    "+5V": VP5V,
                    "+12V": VP12V,
                    "-12V": VN12V,
                    "Temp": TEMP,
                    "MJD": mjd,
                    "Cont OpStatus": CONT,
                    "Beam Current": CURR_BEAM,
                    "C-field Current": CURR_CFIELD,
                    "Ionpump Current": CURR_PUMP,
                    "Gain": GAIN,
                    "RF Amplitude 1": RF_AMP[0],
                    "RF Amplitude 2": RF_AMP[1],
                    "Cesium Oven Voltage": COVEN,
                    "Electron Multiplier Voltage": EMUL,
                    "Hot Wire Ionizer Voltage": HWI,
                    "Mass Spectrometer Voltage": MSP,
                    "DRO Tuning Voltage": PLL9_2,
                    "SAW Tuning Voltage": PLL640,
                    "87 MHz Tuning Voltage": PLL87,
                    "uC clock Tuning Voltage": PLL9
                    }
                }
            ]
            client.write_points(json_body)
            time.sleep(LOGRATE)

def dpm7885_write(SER, S):
    SER.write(str.encode(S+"\r\n"))
    s = SER.readline()
    return s.decode("utf-8").rstrip()

def dpm7885_sync(SER):
    s = SER.readline()
    while s != b'':
        s = SER.readline()

def dpm7885_init(SER):
    dpm7885_write(SER, "")
    dpm7885_write(SER, "$MS")
    dpm7885_sync(SER)
    dpm7885_write(SER, "$SU3")
            
def dpm7885_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE, BAUDRATE, LOGRATE):
    with serial.Serial(SERIALDEVICE, BAUDRATE, bytesize=8, parity='N', stopbits=1, xonxoff=1, timeout=2) as ser:
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)
        # Start up and get Identity
        dpm7885_init(ser)
        # Get ID and Serial numbers
        type = dpm7885_write(ser, "$TT")
        while type == '':
            type = dpm7885_write(ser, "$TT")
        s = dpm7885_write(ser, "$TS")
        while s == '':
            s = dpm7885_write(ser, "$TS")
        s = re.sub(r'\+', '', s)
        snr = int(re.split(r' ', s)[0])
        cynr = int(re.split(r' ', s)[1])
        canr = int(re.split(r' ', s)[2])
        while True:
            try:
                timestamp = datetime.datetime.utcnow().isoformat()
                s = dpm7885_write(ser, "$MR")
                assert is_number(s)
                pressure = 100*float(s)
                s = dpm7885_write(ser, "$MT")
                assert is_number(s)
                temp = float(s)
                assert temp < 200
                #print("%f %f" % (pressure, temp))
                json_body = [
                    {
                        "measurement": MASERID,
                        "tags": {
                            "masertype": "dpm7885",
                            "snr": snr,
                            "cylinernr" : cynr,
                            "calnr": canr
                        },
                        "time": timestamp,
                        "fields": {
                            "Pressure": pressure,
                            "Temp": temp
                        }
                    }
                ]
                client.write_points(json_body)
                time.sleep(LOGRATE)
            except AssertionError as e:
               logging.error(e)
               dpm7885_init(ser)
            except InfluxDBServerError as e:
                logging.error(e)
                client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
                client.create_database(DATABASE)
                client.switch_database(DATABASE)
                time.sleep(1)

def environplus_process(HOST, PORT, DATABASE, MASERID, LOGRATE):
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)
        bus = SMBus(1)
        bme280 = BME280(i2c_dev=bus)
        while True:
            timestamp = datetime.datetime.utcnow().isoformat()
            temperature = bme280.get_temperature()
            pressure = 100.0 * bme280.get_pressure()
            humidity = bme280.get_humidity()
            json_body = [
                {
                    "measurement": MASERID,
                    "tags": {
                        "masertype": "bme280"
                    },
                    "time": timestamp,
                    "fields": {
                        "Pressure": pressure,
                        "Temp": temperature,
                        "Humidity": humidity
                    }
                }
            ]
            client.write_points(json_body)
            time.sleep(LOGRATE)

            
def ticcts_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE):
    with serial.Serial(SERIALDEVICE, 115200, bytesize=8, parity='N', stopbits=1, xonxoff=1, timeout=2) as ser:
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)
        # Sync by throwing first line
        s = ser.readline()
        while True:
            try:
                s = ser.readline().decode("utf-8").rstrip()
                timestamp = datetime.datetime.utcnow().isoformat()
                t = float(re.split(r' ', s)[0])
                ch = re.split(r' ', s)[1]
                if ch == 'chA':
                    ta = t
                    json_body = [
                        {
                            "measurement": MASERID,
                            "tags": {
                                "masertype": "ticc",
                                "mode": "ts"
                            },
                            "time": timestamp,
                            "fields": {
                                "TA": ta
                            }
                        }
                    ]
                    client.write_points(json_body)
                else:
                    tb = t
                    tc = ta - tb
                    json_body = [
                        {
                            "measurement": MASERID,
                            "tags": {
                                "masertype": "ticc",
                                "mode": "ts"
                            },
                            "time": timestamp,
                            "fields": {
                                "TB": tb,
                                "TC": tc
                            }
                        }
                    ]
                    client.write_points(json_body)
            except AssertionError as e:
                logging.error(e)
            except InfluxDBServerError as e:
                logging.error(e)
                client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
                client.create_database(DATABASE)
                client.switch_database(DATABASE)
                time.sleep(1)
            
def vedirect_process(HOST, PORT, DATABASE, MASERID, SERIALDEVICE):
        client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
        client.create_database(DATABASE)
        client.switch_database(DATABASE)        
        ve = Vedirect(SERIALDEVICE, 60)

        def vedirect_callback(packet):
            timestamp = datetime.datetime.utcnow().isoformat()
            for key, value in packet.items():
                #print(key)
                #print(value)
                if key == 'V':
                    V = float(value)/1000
                if key == 'I':
                    I = float(value)/1000
                if key == 'VPV':
                    VPV = float(value)/1000
                if key == 'PPV':
                    PPV = float(value)
                if key == 'IL':
                    IL = float(value)/1000
            #print("V   = %+7.3f V" % V)
            #print("I   = %+7.2f A" % I)
            #print("VPV = %+7.3f V" % VPV)
            #print("PPV = %+7.0f W" % PPV)
            #print("IL  = %+7.2f A" % IL)
            json_body = [
                {
                    "measurement": MASERID,
                    "tags": {
                        "masertype": "vedirect"
                    },
                    "time": timestamp,
                    "fields": {
                        "V": V,
                        "I": I,
                        "VPV": VPV,
                        "PPV": PPV,
                        "IL": IL
                    }
                }
            ]
            client.write_points(json_body)

        while True:
            try:
                #print(ve.read_data_callback(print_data_callback))
                vv = ve.read_data_callback(vedirect_callback)
            except AssertionError as e:
                logging.error(e)
            except InfluxDBServerError as e:
                logging.error(e)
                client = InfluxDBClient(host=HOST, port=PORT, ssl=True, verify_ssl=True)
                client.create_database(DATABASE)
                client.switch_database(DATABASE)
                time.sleep(1)

@click.group()
@click.option('--host', default='localhost', help="InfluxDB host (default localhost)")
@click.option('--port', default=8086, help="InfluxDB port (default 8086)")
@click.option('--database', default='EFOStest', help="InfluxDB database name (default EFOStest)")
@click.option('--maserid', default='maserdata', help="InfluxDB data name for maser data (default maserdata)")
@click.option('--device', default='/dev/ttyUSB0', help="Serial port device (default /dev/ttyUSB0")
@click.option('--baudrate', default=9600 , help="Serial port baudrate (default 9600)")
@click.option('--lograte', default=10, help="Log-rate in seconds (default 10 s)")
@click.pass_context
def maser(ctx, host, port, device, baudrate, database, maserid, lograte):
    ctx.ensure_object(dict)
    ctx.obj['host'] = host
    ctx.obj['port'] = port
    ctx.obj['database'] = database
    ctx.obj['maserid'] = maserid
    ctx.obj['device'] = device
    ctx.obj['baudrate'] = baudrate
    ctx.obj['lograte'] = lograte

@maser.command()
@click.pass_context
def efosb(ctx):
    "EFOS-B active maser protocol"
    print("EFOS-B protocol for %s using device % at rate %i" % (ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate']))
    efosb_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate'], ctx.obj['lograte'])

@maser.command()
@click.pass_context
def vch1006(ctx):
    "VCH1006 passive maser protocol"
    print("VCH1006 protocol for %s using device % at rate %i" % (ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate']))
    vch1006_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate'], ctx.obj['lograte'])
    
@maser.command()
@click.pass_context
def HP5071A(ctx):
    "HP5071A cesium protocol"
    print("HP5071A protocol for %s %s using device % at rate %i" % (ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate']))
    hp5071a_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate'], ctx.obj['lograte'])

@maser.command()
@click.pass_context
def DPM7885(ctx):
    "DPM7885 pressure sensor"
    print("DPM7885 pressure sensor for %s %s using device %s at rate %i" % (ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate']))
    dpm7885_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'], ctx.obj['baudrate'], ctx.obj['lograte'])

@maser.command()
@click.pass_context
def bme280(ctx):
    "Environ+ BME280 sensor"
    print("Environ+ BME280 sensor for %s %s at rate %i" %( ctx.obj['database'], ctx.obj['maserid'], ctx.obj['lograte']))
    environplus_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['lograte'])

@maser.command()
@click.pass_context
def ticcts(ctx):
    "TADR TICC Time Stamp mode"
    print("TADR TICC time-stamp for %s %s using device %s" %( ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device']))
    ticcts_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'])

@maser.command()
@click.pass_context
def vedirect(ctx):
    "VE Direct MPPT mode"
    print("VE Direct MPPT for %s %s using device %s" %( ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device']))
    vedirect_process(ctx.obj['host'], ctx.obj['port'], ctx.obj['database'], ctx.obj['maserid'], ctx.obj['device'])
    
if __name__ == '__main__':
    maser(obj={})

