from contextlib import closing
import json
from socket import create_connection
from socket import timeout
from subprocess_utils import RestartableProcess

class Miner(object):
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        raise NotImplementedError
    
    def stop(self):
        raise NotImplementedError

    def pause(self):
        self.stop()

    def status(self):
        raise NotImplementedError

    def started(self):
        return False

    def paused(self):
        return not self.started()


class CPUMiner(RestartableProcess, Miner):
    """A restartable copy of pooler's cpuminer
    """
    def __init__(self, executable, serverURI, username, password):
        args = [executable,
                '-o', serverURI, '-u', username,
                '-p', password]
        super(CPUMiner, self).__init__(args)
    
    # Inherits start() and stop() from RestartableProcess and
    # pause() from Miner. Multiple inheritance!

    def status(self):
        lines = []
        line = self.check_stderr()
        while line is not None:
            lines.append(line.rstrip())
            line = self.check_stderr()
        return '\n'.join(lines)


class RemoteCGMiner(Miner):
    """A remote copy of cgminer with an open RPC port.
    """
    def __init__(self, address, port=4028, pause_intensity=8,
                 full_intensity=18):
        self.address = address
        self.port = port
        self.n_gpus = self._get_ngpus()
        self.pause_intensity = pause_intensity
        self.full_intensity = full_intensity
    
    def _query(self, command, parameter=''):
        with closing(create_connection((self.address, self.port), 1)) as cxn:
            cxn.send(json.dumps({'command': command,
                                 'parameter': str(parameter)}))
            data = cxn.recv(4096)
        # Remove the trailing null before parsing
        return json.loads(data[:-1])

    def _get_ngpus(self):
        status = self._query('devs')
        return len(status['DEVS'])

    def start(self):
        for gpuid in xrange(self.n_gpus):
            self._query('gpuenable', gpuid)
            self._set_intensity(gpuid, self.full_intensity)

    def pause(self):
        if self.pause_intensity == 0:
            self.stop()
        else:
            for gpuid in xrange(self.n_gpus):
                self._set_intensity(gpuid, self.pause_intensity)

    def stop(self):
        for gpuid in xrange(self.n_gpus):
            self._query('gpudisable', gpuid)

    def _set_intensity(self, gpuid, intensity):
        self._query('gpuintensity', '%d,%s' % (gpuid, intensity))

    def status(self):
        if self.paused():
            return ''
        gpu_statuses = []
        status = self._query('devs')
        for device in status['DEVS']:
            gpu_statuses.append('GPU %d: %.2fK/%.2fKh/s' % (
                device['GPU'],
                device['MHS 5s'] * 1000,
                device['MHS av'] * 1000))
        return '\n'.join(sorted(gpu_statuses))

    def started(self):
        try:
            status = self._query('devs')
        except timeout:
            return False
        return any(gpu['Enabled'] == 'Y' for gpu in status['DEVS'])

    def paused(self):
        status = self._query('devs')
        return all(gpu['Intensity'] == str(self.pause_intensity) or
                   gpu['Enabled'] == 'N'
                   for gpu in status['DEVS'])


class CGMiner(RestartableProcess, RemoteCGMiner):
    def __init__(self, executable, serverURI, username, password,
                 pause_intensity=8, full_intensity=18):
        args = [executable,
                '-o', serverURI,
                '-u', username,
                '-p', password,
                '--scrypt',
                '--api-listen',
                '--api-allow', 'W:127.0.0.1']
        super(CGMiner, self).__init__(args)
        super(RestartableProcess, self).__init__(
            address='127.0.0.1',
            pause_intensity=pause_intensity,
            full_intensity=full_intensity)

    def start(self):
        if not self.started():
            super(RestartableProcess, self).start()
        super(RemoteCGMiner, self).start()

    def stop(self):
        super(RemoteCGMiner, self).stop()
        super(RestartableProcess, self).stop()
