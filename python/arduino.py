from time import sleep
from time import time
from sys import stderr
import json

class ArduinoSensor(object):
    # Packets from the thermostat are JSON, with no
    # newlines in a packet except at the end
    delimiter = '\n'

    def __init__(self, portname, speed=19200):
        from serial import Serial
        port = Serial(baudrate=speed)
        try:
            from serial.win32 import DTR_CONTROL_DISABLE
            port.setDTR(DTR_CONTROL_DISABLE)
        except ImportError:
            print "Warning: Can't use DTR_CONTROL_DISABLE except under Windows"
            print
        except ValueError:
            print "Warning: pySerial 2.6 under Windows is too old"
            print "You must use a newer rev to avoid resetting the board"
            print "upon connection"
            print
        port.port = portname
        port.open()
        self.port = port

    def read_frame(self, _retry_count=0):
        if _retry_count > 3:
            raise IOError('Error communicating with Arduino')

        # Clear the existing buffer to sync up
        waiting = self.port.inWaiting()
        if waiting:
            self.port.read(waiting)

        frame = None
        max_delay = 2  # seconds
        while frame is None:
            self.port.write('read')
            waiting_bytes = 0
            last_waiting = -1
            read_start = time()
            while waiting_bytes != last_waiting or waiting_bytes == 0:
                sleep(0.1)
                last_waiting = waiting_bytes
                waiting_bytes = self.port.inWaiting()
                if time() - read_start > max_delay:
                    return self.read_frame(_retry_count + 1)
            data = self.port.read(waiting_bytes)
            if not (data.startswith('{') and data.endswith('}\n')):
                print >>stderr, 'Bad data, retrying:', data
                continue
            try:
                frame = json.loads(data)
            except ValueError:
                print >>stderr, "Bad frame: ", data
        return frame

    def __iter__(self):
        while True:
            yield self.read_frame()
