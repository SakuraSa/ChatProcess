#!/usr/bin/env python
# coding = utf-8

"""
ChatProcess
"""

__author__ = 'Rnd495'


import multiprocessing
import inspect
import time
from Queue import Empty


class Timer(object):
    """
    Timer
    """
    def __init__(self, lifetime=None):
        self._lifetime = lifetime
        self._time_cost = 0
        self._last_begin = None

    @property
    def has_lifetime(self):
        return self._lifetime is not None

    @property
    def is_timeout(self):
        if self.has_lifetime:
            return self.remain <= 0
        else:
            return False

    @property
    def lifetime(self):
        """
        :return: lifetime of this timer
        """
        return self._lifetime

    @property
    def time_cost(self):
        """
        :return: lifetime that this timer has already used
        """
        return self._time_cost

    @property
    def remain(self):
        """
        :return: remain lifetime of this timer
        """
        if self.has_lifetime:
            return self._lifetime - self._time_cost
        else:
            return None

    def __enter__(self):
        if self.is_timeout:
            raise TimeoutError()
        self._last_begin = time.time()
        return self

    def __exit__(self, *_):
        self._time_cost += time.time() - self._last_begin

    def addon_timeout(self, timeout=None):
        if timeout is None:
            return self.remain
        if not self.has_lifetime:
            return timeout
        return min(self.remain, timeout)


class ChatProcess(multiprocessing.Process):
    """
    ChatProcess
    """
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        """
        :param group: group argument must be None for now
        :param target: target function will be running on this process
        :param name: process name
        :param args: args for target function
        :param kwargs: kwargs for target function
        """
        target_args = inspect.getargspec(target).args
        assert '_in_queue' in target_args, 'target func should contains the arg named as "_in_queue"'
        assert '_out_queue' in target_args, 'target func should contains the arg named as "_out_queue"'
        kwargs = {} if kwargs is None else kwargs
        assert '_in_queue' not in kwargs, 'kwargs should not contains the arg named as "_in_queue"'
        assert '_out_queue' not in kwargs, 'kwargs should not contains the arg named as "_out_queue"'
        multiprocessing.Process.__init__(self, group, target, name, args, kwargs)
        self._in_queue = multiprocessing.Queue()
        self._out_queue = multiprocessing.Queue()
        self._kwargs['_in_queue'] = self._out_queue
        self._kwargs['_out_queue'] = self._in_queue

    @property
    def in_queue(self):
        return self._in_queue

    @property
    def out_queue(self):
        return self._out_queue

    def start(self):
        multiprocessing.Process.start(self)
        return self

    def put(self, data, timeout=None):
        """
        sent data to this process
        :param data: data
        :param timeout: timeout
        :return: None
        """
        if timeout is not None and timeout <= 0:
            raise TimeoutError()
        try:
            self._in_queue.put(data, timeout=timeout)
        except Empty:
            raise TimeoutError()

    def get(self, timeout=None):
        """
        poll data from this process
        :param timeout: timeout
        :return: data
        """
        if timeout is not None and timeout <= 0:
            raise TimeoutError()
        try:
            value = self._out_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError()
        if isinstance(value, ProcessError):
            raise value
        else:
            return value

    def chat(self, data, timeout=None):
        """
        poll data after sent data
        :param data: data
        :param timeout: timeout
        :return: data
        """
        if timeout is not None and timeout <= 0:
            raise TimeoutError()
        begin = time.time()
        self.put(data, timeout=timeout)
        if timeout is not None:
            remain = timeout - (time.time() - begin)
            if remain <= 0:
                raise TimeoutError()
            else:
                timeout = remain
        return self.get(timeout=timeout)


class TimeoutError(Exception):
    """
    TimeoutError
    """
    def __str__(self):
        return 'TimeoutError'


class ProcessError(Exception):
    """
    ProcessError
    """
    def __init__(self, message, inner_error=None):
        Exception.__init__(self, message, inner_error)
        self.message = message
        self.inner_error = inner_error


class ChatProcessWithLifetime(ChatProcess, Timer):
    """
    ChatProcessWithLifetime
    """
    def __init__(self, lifetime, group=None, target=None, name=None, args=(), kwargs=None):
        """
        :param lifetime: the total lifetime this process has
        :param group: group argument must be None for now
        :param target: target function will be running on this process
        :param name: process name
        :param args: args for target function
        :param kwargs: kwargs for target function
        """
        kwargs = {} if kwargs is None else kwargs
        ChatProcess.__init__(self, group, target, name, args, kwargs)
        Timer.__init__(self, lifetime)

    def __enter__(self):
        try:
            Timer.__enter__(self)
        except Exception, error:
            # suicide
            self.terminate()
            raise error

    def __exit__(self, exc_type, exc_val, exc_tb):
        Timer.__exit__(self, exc_type, exc_val, exc_tb)
        if exc_val:
            # suicide
            self.terminate()

    def put(self, data, timeout=None):
        """
        sent data to this process
        :param data: data
        :param timeout: timeout
        :return: None
        """
        with self:
            return ChatProcess.put(self, data, timeout=self.addon_timeout(timeout))

    def get(self, timeout=None):
        """
        poll data from this process
        :param timeout: timeout
        :return: data
        """
        with self:
            return ChatProcess.get(self, timeout=self.addon_timeout(timeout))

    def chat(self, data, timeout=None):
        """
        poll data after sent data
        :param data: data
        :param timeout: timeout
        :return: data
        """
        with self:
            return ChatProcess.chat(self, data, timeout=self.addon_timeout(timeout))


class Chatroom(object):
    """
    Chatroom
    """
    def __init__(self, in_queue, out_queue):
        object.__init__(self)
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._running = True

    @property
    def in_queue(self):
        return self._in_queue

    @property
    def out_queue(self):
        return self._out_queue

    @property
    def running(self):
        return self._running

    def put(self, data):
        self._in_queue.put(data)

    def get(self):
        return self._out_queue.get()

    def stop(self):
        self._running = False

    def response(self, data):
        raise NotImplementedError()

    def _loop(self):
        while self._running:
            data = self.get()
            value = self.response(data)
            self.put(value)

    @classmethod
    def _process_entries(cls, _in_queue, _out_queue, *args, **kwargs):
        try:
            chatroom = cls(in_queue=_in_queue, out_queue=_out_queue, *args, **kwargs)
        except Exception, error:
            _in_queue.put(ProcessError(message='Error occurred on initialization', inner_error=error))
            return
        try:
            chatroom._loop()
        except Exception, error:
            _in_queue.put(ProcessError(message='Error occurred on loop', inner_error=error))
            return

    @classmethod
    def create_process(cls, lifetime=None, *args, **kwargs):
        return ChatProcessWithLifetime(
            lifetime=lifetime,
            target=cls._process_entries,
            name=cls.__name__,
            args=args, kwargs=kwargs)