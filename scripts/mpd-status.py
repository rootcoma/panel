#! /bin/python
from mpd import MPDClient, ConnectionError
from time import sleep
from argparse import ArgumentParser
from signal import SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM, signal
from sys import stdout, stderr, maxint

# Formatting values:
#   %s - seek time ([h:]mm:ss)
#   %n - total time ([h:]mm:ss)
#   %t - title
#   %x - state (paused, stopped, play)
#   %a - artist
#   %b - album
#   %l - number of items in playlist
#   %w - playlist item playing
#   %v - volume (0-100)
#   %r - repeat (note: useful with conditionals)
#   %d - random (note: useful with conditionals)
# Conditionals:
#   ?<formatting value>@<things to show if exists>@
#   eg "?a@%a - @" - only shows artist if it is not ''

# TODO:
# create sections to contain items together with max length
# &<max length>{<section goes here}
# eg "&20{%a - %t}"


RECONNECT_TIMEOUT = 10
UPDATE_TIMEOUT = 1
client = None

# options
format = '%s/%n %t'
format_not_playing = '%x %t'
format_disconnected = 'disconnected'
length_limit = 0
scroll = 0
state_play_string = 'playing'
state_stop_string = 'stopped'
state_pause_string = 'paused'
scrolling_enabled = False
continuous = False

# formatting replacements
format_items = {
    's': ('status', 'seek'),
    'n': ('status', 'total_time'),
    't': ('currentsong', 'title'),
    'x': ('status', 'state_string'),
    'a': ('currentsong', 'artist'),
    'b': ('currentsong', 'album'),
    'l': ('status', 'playlistlength'),
    'w': ('status', 'song'),
    'v': ('status', 'volume'),
    'r': ('status', 'repeat'),
    'd': ('status', 'random')
}

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

def check_key_equals(l, key, value):
    if l is None:
        return False
    if key not in l:
        return False
    if l[key] == value:
        return True

def get_value_or_none(l, key):
    if l is None:
        return None
    if key not in l:
        return None
    return l[key]

def get_value_or_empty_string(l, key):
    val = get_value_or_none(l, key)
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

def parse_conditionals(format_line, info):
    new_line = ''
    line_length = len(format_line)
    toggle_ignore = False
    skip = 0
    num_open_tags = 0

    debug = ''
    for offset in range(line_length):
        c = format_line[offset]
        if c == '?':
            if offset < line_length-3:
                if format_line[offset+1] in format_items:
                    offset_item = format_items[format_line[offset+1]]
                    if format_line[offset+2] == '@':
                        skip = 2
                        if num_open_tags > 0:
                            num_open_tags += 1
                            continue
                        # we have conditional, check if value exists
                        newvalue = get_value_or_empty_string(info[offset_item[0]], offset_item[1])
                        if newvalue == '':
                            toggle_ignore = True
                            num_open_tags += 1
                        continue
        if c == '@' and skip == 0:
            debug = '%s^' % debug
            if toggle_ignore and num_open_tags > 0:
                num_open_tags -= 1
            if num_open_tags == 0:
                toggle_ignore = False
            continue
        if not toggle_ignore and skip == 0:
            new_line = '%s%c' % (new_line, c)
        if skip > 0:
            skip -= 1
    return new_line


def format_line(info):
    global scroll
    status = get_value_or_none(info, 'status')
    currentsong = get_value_or_none(info, 'currentsong')
    #decide the format, and adjust some wording for state
    original_line = format

    state = get_value_or_empty_string(status, 'state')
    if state == "play":
        original_line = format
    elif state == 'stop' or state == 'pause':
        original_line = format_not_playing
    else:
        original_line = format_disconnected
        return original_line

    original_line = parse_conditionals(original_line, info)

    new_line = original_line
    for offset in range(len(original_line)):
        c = original_line[offset]
        if c == '%':
            if offset < len(original_line)-1:
                if original_line[offset+1] in format_items:
                    combo = "%c%c" % (original_line[offset], original_line[offset+1])
                    offset_item = format_items[original_line[offset+1]]
                    newvalue = get_value_or_empty_string(info[offset_item[0]], offset_item[1])
                    if length_limit > 0:
                        if len(newvalue) > length_limit:
                            # do scroll
                            original_value = newvalue
                            offset = scroll%(len(newvalue)+1)
                            newvalue = newvalue[offset:offset+length_limit]

                            overflow = len(original_value)-offset
                            if overflow < length_limit:
                                newvalue = "%s %s" % (newvalue, original_value[:length_limit-overflow-1])
                    new_line = new_line.replace(combo, newvalue)
    if scrolling_enabled:
        scroll += 1
        # TODO find a better way to wrap around
        if scroll >= maxint:
            scroll = 0
    return new_line

def output(str):
    stdout.write("%s\n" % str)
    stdout.flush()

def output_error(str):
    stderr.write("%s\n" % str)
    stderr.flush()

def create_info(status, currentsong):
    state = get_value_or_empty_string(status, 'state')
    if state == 'play':
        status['state_string'] = state_play_string
    elif state == 'stop':
        status['state_string'] = state_stop_string
    elif state == 'pause':
        status['state_string'] = state_pause_string


    random = get_value_or_none(status, 'random')
    if random is not None:
        if random != '1':
            status['random'] = None
    repeat = get_value_or_none(status, 'repeat')
    if repeat is not None:
        if repeat != '1':
            status['repeat'] = None

    time = get_value_or_none(status, 'time')
    if time is not None:
        time_split = time.split(':')
        if len(time_split) == 2:
            seek, total_time = time_split
            status['seek'] = format_time(seek)
            status['total_time'] = format_time(total_time)
    if get_value_or_none(status, 'song') is not None:
        if status['song'].isdigit():
            status['song'] = str(int(status['song'])+1)

    return {'status': status, 'currentsong': currentsong}

def main_loop():
    while True:
        try:   
            status = client.status()
            currentsong = client.currentsong()
            info = create_info(status, currentsong) #create a single dict
            output(format_line(info))
        except ConnectionError:  
            #output_error("Error: disconnected")
            output(format_line(None))
            sleep(RECONNECT_TIMEOUT)
            connect()
        else:
            if not continuous:
                disconnect()
                exit(0)
            if check_key_equals(status, 'state', 'stop'):
                sleep(UPDATE_TIMEOUT)
                try:
                    client.idle()
                except:
                    pass
            elif check_key_equals(status, 'state', 'pause'):
                sleep(UPDATE_TIMEOUT)
                try:
                    client.idle()
                except:
                    pass
            else:
                sleep(UPDATE_TIMEOUT)

def init():
    global client
    parse_args()
    client = MPDClient()
    connect()

def sig_handler(signum, frame):
    disconnect()    
    exit(1)

def parse_args():
    global format
    global format_not_playing
    global format_disconnected
    global length_limit
    global scrolling_enabled
    global continuous
    parser = ArgumentParser(description='Output MPD status.', prog="mpd-status.py")
    parser.add_argument('-f', '--format', dest='format', help='format of output')
    parser.add_argument('-n', '--format-not-playing', dest='format_not_playing', help='format of output when not playing')
    parser.add_argument('-d', '--format-disconnected', dest='format_disconnected', help='format when disconnected')
    parser.add_argument('-l', '--length-limit', type=int, dest='length_limit', help='set max length for any string')
    parser.add_argument('-s', '--scrolling-enabled', action='store_true', dest='scrolling_enabled', help='enable scrolling for long strings')
    parser.add_argument('-c', '--continuous', action='store_true', dest='continuous', help='coninuously output')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    args = parser.parse_args()
    if args.length_limit is not None:
        length_limit = args.length_limit
    if args.format_disconnected is not None:
        format_disconnected = args.format_disconnected
    if args.format_not_playing is not None:
        format_not_playing = args.format_not_playing
    if args.continuous is not None:
        continuous = args.continuous
    if args.format is not None:
        format = args.format
    if args.scrolling_enabled is not None:
        scrolling_enabled = args.scrolling_enabled

def do_main():
    init()
    main_loop()

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, sig_handler)
do_main()

