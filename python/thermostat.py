from ConfigParser import RawConfigParser
from Queue import Queue, Empty
from subprocess import Popen
from subprocess import PIPE
from threading import Lock
from threading import Thread

from arduino import ArduinoSensor

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
        self._stdout_queue = Queue()
        self._stderr_queue = Queue()
        self._stdout_flag = Flag()
        self._stderr_flag = Flag()
        self._stdout_thread = Thread(
            target=NonblockingPipeProcess.enqueue_output,
            args=(self.stdout, self._stdout_queue, self._stdout_flag))
        self._stdout_thread.daemon = True
        self._stderr_thread = Thread(
            target=NonblockingPipeProcess.enqueue_output,
            args=(self.stderr, self._stderr_queue, self._stderr_flag))
        self._stderr_thread.daemon = True
        self._stdout_thread.start()
        self._stderr_thread.start()
    
    def terminate(self):
        self._stdout_flag.set()
        self._stderr_flag.set()
        super(NonblockingPipeProcess, self).terminate()
        try:
            self._stdout_thread.join()
        except RuntimeError:
            pass
        try:
            self._stderr_thread.join()
        except RuntimeError:
            pass

    def _check_q(self, queue):
        try:
            return queue.get_nowait()
        except Empty:
            return None
    
    def check_stdout(self):
        return self._check_q(self._stdout_queue)

    def check_stderr(self):
        return self._check_q(self._stderr_queue)


class CPUMiner(object):
    def __init__(self, executable, serverURI, username, password):
        self.args = [executable,
                     '-o', serverURI, '-u', username,
                     '-p', password]
        self.started = False

    def start(self):
        if self.started:
            return
        self.process = NonblockingPipeProcess(self.args)
        self.process.poll()
        if self.process.returncode is None:
            self.started = True
        else:
            print self.process.returncode
            raise "Not Started!"
            self.process = None

    def stop(self):
        if self.process is not None and self.started:
            self.process.terminate()
            self.process.wait()
            self.started = False
            self.process = None

    def check_stderr(self):
        if self.process is not None:
            return self.process.check_stderr()
        else:
            return None

    def check_stdout(self):
        if self.process is not None:
            return self.process.check_stdout()
        else:
            return None


def load_mining_config(config_file='miners.cfg'):
    parser = RawConfigParser()
    parsed = parser.read(config_file)
    if parsed != [config_file]:
        raise ValueError('Could not parse config file')
    miners = {}
    for miner_name in parser.sections():
        assert miner_name not in miners
        miner_type = parser.get(miner_name, 'type')
        if miner_type == 'cpu':
            executable = parser.get(miner_name, 'executable')
            server = parser.get(miner_name, 'server')
            username = parser.get(miner_name, 'username')
            password = parser.get(miner_name, 'password')
            miners[miner_name] = CPUMiner(
                executable=executable,
                serverURI=server,
                username=username,
                password=password)
        else:
            raise ValueError('Did not understand miner type %s' % miner_type)
    return miners


def main():
    sensor = ArduinoSensor('COM7', speed=19200)
    miners = load_mining_config()
    for miner in miners.itervalues():
        miner.start()
    for i in range(50):
        print sensor.read_frame()
        for miner_name, miner in miners.iteritems():
            line = miner.check_stderr()
            while line is not None:
                print miner_name, line.rstrip()
                line = miner.check_stderr()
    for miner in miners.itervalues():
        miner.stop()
    

if __name__ == '__main__':
    main()
