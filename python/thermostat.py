from ConfigParser import RawConfigParser
from Queue import Queue, Empty
from subprocess import Popen
from subprocess import PIPE
from threading import Lock
from threading import Thread
from time import sleep
from time import time

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


class CPUMiner(object):
    def __init__(self, executable, serverURI, username, password):
        self.args = [executable,
                     '-o', serverURI, '-u', username,
                     '-p', password]
        self.started = False
        self.process = None

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
        else:
            print self.process
            print self.started
            print "Unable to terminate!"

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
            miners[miner_name] = CPUMiner(
                executable=parser.get(miner_name, 'executable'),
                serverURI=parser.get(miner_name, 'server'),
                username=parser.get(miner_name, 'username'),
                password=parser.get(miner_name, 'password'))
        else:
            raise ValueError('Did not understand miner type %s' % miner_type)
    return miners


class Thermostat(object):
    def __init__(self, port, speed=19200):
        self.sensor = ArduinoSensor(port, speed)
        self.dead_zone = 1

    def check(self):
        sense = self.sensor.read_frame()
        temp = sense['temperature']
        setp = sense['setpoint']
        if (temp - setp) > self.dead_zone:
            # Temperature is too high
            return temp, 1
        elif (setp - temp) > self.dead_zone:
            # Temperature is too low
            return temp, -1
        else:
            # We're within the dead zone
            return temp, 0


def main():
    thermostat = Thermostat('COM7', speed=19200)
    miners = load_mining_config()
    
    last_checked_time = 0
    control_interval = 60  # Seconds
    while True:
        # Check temperature
        if time() - last_checked_time > control_interval:
            last_checked_time = time()
            temperature, control = thermostat.check()
            control_string = {0: 'OK', 1: 'too high', -1: 'too low'}[control]
            print '---- Temperature check ----'
            print 'Current temp:', temperature, 'C,', control_string
            for name, miner in miners.iteritems():
                if miner.started and control > 0:
                    print 'Stopping', name
                    miner.stop()
                elif not miner.started and control < 0:
                    print 'Starting', name
                    miner.start()
            print '---------------------------'
        # Output from each miner
        for miner_name, miner in miners.iteritems():
            line = miner.check_stderr()
            while line is not None:
                print miner_name, line.rstrip()
                line = miner.check_stderr()
        sleep(1)

if __name__ == '__main__':
    main()
