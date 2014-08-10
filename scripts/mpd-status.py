#! /bin/python
from mpd import MPDClient, ConnectionError
from time import sleep
from argparse import ArgumentParser
from signal import *
import sys
#import os

#unbuffered_stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
#unbuffered_stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

#sys.stdout = unbuffered_stdout
#sys.stderr = unbuffered_stderr

RECONNECT_TIMEOUT = 10
UPDATE_TIMEOUT = 1
client = None
format = '%s/%n %t'
format_not_playing = '%x %t'
format_disconnected = 'disconnected'

def connect():
    global client
    client.timeout = 10
    client.idletimeout = None
    try:
        client.connect("localhost", 6600)
    except:
        pass

def disconnect():
    global client
    try:
        client.close()
    except:
        pass
    try:
        client.disconnect()
    except:
        pass

def checkValueEquals(l, key, value):
    if l is None:
        return False
    if key not in l:
        return False
    if l[key] == value:
        return True

def getValueOrNone(l, key):
    if l is None:
        return None
    if key not in l:
        return None
    return l[key]

def getValueOrEmptyString(l, key):
    val = getValueOrNone(l, key)
    if val is None:
        return ''
    return val

def format_time(seconds):
    if seconds < 60:
        return seconds
    minutes, seconds  = divmod(int(seconds), 60)
    if minutes < 60:
        return "%02d:%02d" % (minutes,seconds)
    hours, minutes = divmod(int(minutes), 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def format_line(status, currentsong):
    newline = format
    state = getValueOrEmptyString(status, 'state')
    if state == "play":
        newline = format
    elif state == "stop" or state == "pause":
        newline = format_not_playing
        if state == "stop":
            state = "%sped" % state
        else:
            state = "%sd" % state
    else:
        newline = format_disconnected
        return newline

    time = getValueOrNone(status, "time")
    
    seek = ''
    totalTime = ''
    if time is not None:
        seek, totalTime = time.split(":")
        seek = format_time(seek)
        totalTime = format_time(totalTime)
    
    title = getValueOrEmptyString(currentsong, "title") 

    newline = newline.replace("%s", seek)
    newline = newline.replace("%n", totalTime)
    newline = newline.replace("%t", title)
    newline = newline.replace("%x", state)                                                             
    return newline

def output(str):
    sys.stdout.write("%s\n" % str)
    sys.stdout.flush()

def output_error(str):
    sys.stderr.write("%s\n" % str)
    sys.stderr.flush()

def mainLoop():
    while True:
        try:   
            status = client.status()
            currentsong = client.currentsong()
            output(format_line(status, currentsong)) 
        except ConnectionError:  
            #output_error("Error: disconnected")
            output(format_line(None, None))
            sleep(RECONNECT_TIMEOUT)
            connect()
        else:
            if checkValueEquals(status, 'state', 'stop'):
                client.idle()
            elif checkValueEquals(status, 'state', 'pause'):
                client.idle()
            else:
                sleep(UPDATE_TIMEOUT)

def init():
    global client
    parseArgs()
    client = MPDClient()
    connect()

def sig_handler(signum, frame):
    disconnect()    
    exit(1)

def parseArgs():
    global format
    global format_not_playing
    global format_disconnected
    parser = ArgumentParser(description='Output MPD status.')
    parser.add_argument('-f', '--format', dest='format', help='format of output')
    parser.add_argument('-n', '--format-not-playing', dest='format_not_playing', help='format of output when not playing')
    parser.add_argument('-d', '--format-disconnected', dest='format_disconnected', help='format when disconnected')
    args = parser.parse_args()
    if args.format_disconnected is not None:
        format_disconnected = args.format_disconnected
    if args.format_not_playing is not None:
        format_not_playing = args.format_not_playing
    if args.format is not None:
        format = args.format

def doMain():
    init()
    mainLoop()

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, sig_handler)
doMain()

