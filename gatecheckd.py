#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# Copyright (c) 2020 Pakorn C.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import subprocess
import re
import board, busio, adafruit_vl53l0x
import sentry_sdk
import requests

# External IP check URL
IPCHECKURL = ''

# Sentry error tracking
SENTRYDSN = ''
sentry_sdk.init(SENTRYDSN)

# I2C device address
I2CADDR = '0x29'

# Telegram API information
TGTOKEN = ''
TGBASEURL = ''

# Debug message recipients
DBGRCPT = []

# Normal message recipients
RCPT = []

# Range threshold for opened gate (mm)
THRESHOLD = 200

# Check period in seconds
CHECKPERIOD = 2 

# Number of repeating status before official state change
CFSLOT = 5 

# Long gate open timeout (minutes)
LONGOPENTIME = 5

# Global objects
IPMATCH = re.compile('inet ([0-9/\.]+)')
GATEOPEN = False
LONGSTATECOUNT = 0

def getstartupmsg():
    msg = '<b>Gatekeeper Daemon Started</b>\n'
    # Internal IP
    cmd = ['ip','addr','show','wlan0']
    po = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    po.wait()
    match = IPMATCH.search(po.stdout.read().decode('ascii'))
    if match is not None:
        msg += f'Internal IP: {match.groups()[0]}\n'
    else:
        msg += 'Internal IP: N/A\n'
    try:
        req = requests.get(IPCHECKURL)
        if req.status_code == 200:
            ipinfo = req.json()
            msg += f'External IP: {ipinfo["ip"]}\n'
        else:
            msg += 'External IP: N/A\n'
    except:
        msg += 'External IP: N/A\n'
    cmd = ['i2cget', '-y', '1', I2CADDR]
    po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    po.wait()
    if po.returncode == 0:
        msg += 'TOF Sensor: Present\n'
    else:
        msg += 'TOF Sensor: Not present\n'
    return msg

def getrange():
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_vl53l0x.VL53L0X(i2c)
    return sensor.range

def _log(msg):
    print(f"""{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}""")

def checklongstate():
    global LONGSTATECOUNT
    totalslotperiod = CFSLOT * CHECKPERIOD
    mustopen = LONGOPENTIME * 60
    mustrepeat = mustopen / totalslotperiod
    if all(statecheck):
        LONGSTATECOUNT += 1
        if LONGSTATECOUNT >= mustrepeat:
            for i in RCPT:
                _log('Long state notification')
                sendmsg(i, f'<b>Gate opened for longer than {LONGOPENTIME} minute(s)</b>')
            LONGSTATECOUNT = 0
    else:
        LONGSTATECOUNT = 0
    return True

def sendmsg(rcpt, msg):
    param = {
        'chat_id': rcpt,
        'parse_mode': 'HTML',
        'text': f"""{time.strftime("%d-%b-%Y %H:%M:%S")}\n{msg}"""
    }
    try:
        req = requests.post(f'{TGBASEURL}{TGTOKEN}/sendMessage', json=param)
        if req.status_code == 200:
            return True
        else:
            print(req.json())
        return False
    except:
        return False

if __name__ == '__main__':
    _log('Starting up')
	startupdata = getstartupmsg()
    for i in DBGRCPT:
        sendmsg(i, startupdata)
    statecheck = [ False for i in range(CFSLOT) ]
    rangecheck = [ 0 for i in range(CFSLOT) ]
    statecounter = 0
    while True:
        objrange = getrange()
        rangecheck[statecounter] = objrange
        if objrange <= THRESHOLD:
            statecheck[statecounter] = True
        else:
            statecheck[statecounter] = False
        if all(statecheck) and not GATEOPEN:
            _log('Gate opened')
            GATEOPEN = True
            for i in RCPT:
                if i not in DBGRCPT:
                    sendmsg(i, '<b>Gate opened</b>')
                else:
                    sendmsg(i, f'<b>Gate opened</b> {rangecheck}')
        elif not any(statecheck) and GATEOPEN:
            _log('Gate closed')
            GATEOPEN = False
            for i in RCPT:
                if i not in DBGRCPT:
                    sendmsg(i, '<b>Gate closed</b>')
                else:
                    sendmsg(i, f'<b>Gate closed</b> {rangecheck}')
        if statecounter == len(statecheck) - 1:
            statecounter = 0
            checklongstate()
        else:
            statecounter += 1
        time.sleep(CHECKPERIOD)
