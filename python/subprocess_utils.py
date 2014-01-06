from Queue import Queue
from Queue import Empty
from subprocess import Popen
from subprocess import PIPE
from threading import Lock
from threading import Thread

class Flag(object):
    def __init__(self):
        self.lock = Lock()
        self.is_set = False
    
    def check(self):
        with self.lock:
            is_set = self.is_set
        return is_set

    def set(self):
        with self.lock:
            self.is_set = True


class NonblockingPipeProcess(Popen):
    """
    Inspired by
    https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    """

    @staticmethod
    def enqueue_output(source, queue, flag):
        for line in iter(source.readline, b''):
            queue.put(line)
            if flag.check():
                print "Quitting thread"
                break
        source.close()

    def __init__(self, *args, **kwargs):
        assert 'stdout' not in kwargs
        assert 'stderr' not in kwargs
        super(NonblockingPipeProcess, self).__init__(
                stdout=PIPE,
                stderr=PIPE,
                *args, **kwargs)
        self.queues = {}
        self.setup_queue('stdout', self.stdout)
        self.setup_queue('stderr', self.stderr)
        for queue in self.queues.itervalues():
            queue['thread'].start()

    def setup_queue(self, name, stream):
        queue = Queue()
        flag = Flag()
        thread = Thread(
            target=NonblockingPipeProcess.enqueue_output,
            args=(stream, queue, flag))
        thread.daemon = True

        self.queues[name] = {}
        self.queues[name]['queue'] = queue
        self.queues[name]['flag'] = flag
        self.queues[name]['thread'] = thread

    def terminate(self):
        # Have to terminate the process first so that the threads'
        # pipe reads terminate, and they get the signal to die.
        super(NonblockingPipeProcess, self).terminate()
        for queue in self.queues.itervalues():
            queue['flag'].set()
            queue['thread'].join()

    def _check_q(self, queue):
        try:
            return self.queues[queue]['queue'].get_nowait()
        except Empty:
            return None
    
    def check_stdout(self):
        return self._check_q('stdout')

    def check_stderr(self):
        return self._check_q('stderr')


class RestartableProcess(object):
    def __init__(self, args):
        self._args = args
        self._started = False
        self._process = None

    def start(self):
        if self._started:
            return
        self._process = NonblockingPipeProcess(self._args)
        self._process.poll()
        if self._process.returncode is None:
            self._started = True
        else:
            print self._process.returncode
            raise OSError('Could not start process')
            self.process = None

    def stop(self):
        if self._process is not None and self._started:
            self._process.terminate()
            self._process.wait()
            self._started = False
            self._process = None

    def check_stderr(self):
        if self._process is not None:
            return self._process.check_stderr()
        else:
            return None

    def check_stdout(self):
        if self._process is not None:
            return self._process.check_stdout()
        else:
            return None

    def started(self):
        return self._started
