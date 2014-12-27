#!/usr/bin/env python
# coding = utf-8

"""
example
"""

__author__ = 'Rnd495'

from time import sleep
from ChatProcess import Chatroom


class Echo(Chatroom):
    """
    Echo
    """
    def response(self, data):
        if data.startswith('sleep'):
            sec = float(data[6:])
            sleep(sec)
            return 'wake up after %dms' % (sec * 1000)
        elif data:
            return data
        else:
            self.stop()
            return 'goodbye'


if __name__ == '__main__':
    from ChatProcess import TimeoutError, ProcessError

    print 'process 01:'
    e = Echo.create_process(lifetime=1).start()
    print e.chat('Hello world!'), e.remain
    print e.chat('sleep:0.1'), e.remain
    print e.chat(''), e.remain

    print ''
    print 'process 02:'
    e = Echo.create_process(lifetime=1).start()
    try:
        print e.chat('Hello world!'), e.remain
        print e.chat('sleep:1.0'), e.remain
        print e.chat(''), e.remain
    except TimeoutError, error:
        print 'error:', error

    print ''
    print 'process 03:'
    e = Echo.create_process(lifetime=1).start()
    try:
        print e.chat('Hello world!'), e.remain
        print e.chat('sleep:not a num'), e.remain
        print e.chat(''), e.remain
    except ProcessError, error:
        print 'error:', error
