from ConfigParser import RawConfigParser
from datetime import datetime
from sys import stdin
from time import sleep
from time import time

from arduino import ArduinoSensor
from miners import CGMiner
from miners import CPUMiner
from miners import RemoteCGMiner

import platform
if platform.system() == "Windows":
    from msvcrt import kbhit
else:
    import select
    def kbhit():
        inrdy, _, __ = select.select([stdin], [], [], 0.001)
        return len(inrdy) > 0


def check_keyboard():
    if kbhit():
        raise KeyboardInterrupt
    return


def load_mining_config(config_file='miners.cfg'):
    parser = RawConfigParser()
    parsed = parser.read(config_file)
    if parsed != [config_file]:
        raise ValueError('Could not parse config file')

    miner_type2args = {
        'cpu': (CPUMiner, ['executable', 'serverURI', 'username', 'password']),
        'cgminer-remote': (RemoteCGMiner, ['address', 'pause_intensity',
                                           'full_intensity']),
        'cgminer': (CGMiner, ['executable', 'serverURI', 'username', 'password',
                              'pause_intensity', 'full_intensity',
                              'delay', 'work_unit', 'thread_concurrency']),
    }

    miners = {}
    for miner_name in parser.sections():
        assert miner_name not in miners

        miner_type = parser.get(miner_name, 'type')
        if miner_type not in miner_type2args:
            raise ValueError('Did not understand miner type %s' % miner_type)

        miner_class, arg_names = miner_type2args[miner_type]
        # Developing on a Python 2.6 machine, arg...
        args = dict((arg, parser.get(miner_name, arg)) for arg in arg_names)
        print "Adding miner", miner_name, "of type", miner_type, "with options",
        print args
        miners[miner_name] = miner_class(**args)
    return miners


class Thermostat(object):
    def __init__(self, port, speed=19200):
        self.sensor = ArduinoSensor(port, speed)
        self.dead_zone = 0.5 

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
    thermostat = Thermostat('COM3', speed=19200)
    miners = load_mining_config()
    
    last_checked_time = 0
    control_interval = 60  # Seconds
    while True:
        try:
            check_keyboard()
        except KeyboardInterrupt:
            break
        # Check temperature
        if time() - last_checked_time > control_interval:
            last_checked_time = time()
            temperature, control = thermostat.check()
            control_string = {0: 'OK', 1: 'too high', -1: 'too low'}[control]
            curtime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            print '---- Temperature check %s ----' % curtime
            print 'Current temp:', temperature, 'C,', control_string
            for name, miner in miners.iteritems():
                if control > 0 and (miner.started() and not miner.paused()):
                    print 'Pausing', name
                    miner.pause()
                elif control < 0 and (miner.paused() or not miner.started()):
                    print 'Resuming', name
                    miner.start()
            print '---------------------------'
        # Output from each miner
        for miner_name, miner in miners.iteritems():
            lines = miner.status()
            if lines:
                for line in lines.split('\n'):
                    print miner_name, line.rstrip()
        sleep(5)

    for miner in miners.itervalues():
        miner.stop()

if __name__ == '__main__':
    main()
