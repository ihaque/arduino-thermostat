# arduino-thermostat

Uses an Arduino equipped with temperature probe to control a heat-generating
PC to keep your room at a cozy temperature.

![Thermostat picture](https://raw.githubusercontent.com/ihaque/arduino-thermostat/master/thermostat.jpg)

## Materials
1. Arduino Uno
2. [DS18B20-based One-Wire temperature probe](https://www.adafruit.com/products/381)
3. [Serial LCD](https://www.sparkfun.com/products/9394)
4. Input device for Arduino. I had a [CAN-BUS shield](https://www.sparkfun.com/products/13262) with built-in joystick lying around from [another project](https://github.com/ihaque/arduino-ecu-logger).

## Arduino Side

The Arduino is used as a dumb sensor and interface device. The LCD shows the
current temperature and the setpoint, which can be adjusted using the joystick.
The Arduino runs in a loop: after initializing the DS18B20 to 11-bit precision,
every 375 ms it polls the thermometer for its current temperature. If the PC on
the other end of the serial interface has sent the ASCII string `read`
(non-null terminated) since the last polling event, the Arduino then sends a
JSON-formatted blob of the current temperature and the setpoint over the
serial connection.

Serial communications takes place at 19.2kbps for reliability; not much data
needs to move across the wire, so it's fine to go slow.

## PC Side

All the intelligence of the thermostat is on the PC side, implemented in Python.

Class `Thermostat` implements a simple bang-bang controller with dead zone to
decide whether to activate, deactivate, or hold the current state of the
"heating elements" (actually, CPU/GPU intensive programs). `main()` in
thermostat.py periodically polls the Arduino for the current temperature and
setpoint, passing this to the `Thermostat` object for a control decision.

When I wrote this code, I was mining the Litecoin and Dogecoin cryptocurrencies,
using [pooler's cpuminer](https://github.com/pooler/cpuminer) to mine on the CPU
and [CGMiner](http://ck.kolivas.org/apps/cgminer/) to mine on my AMD GPU.
cpuminer is easy to turn on and off: just start or kill the process. However,
cgminer (or the graphics driver) is not happy with being killed and restarted
too many times; thus I control it with the remote RPC call support.

`subprocess_utils.py` has some neat tricks for handling subprocesses. The class
`NonblockingPipeProcess` implements a subclass of `subprocess.Popen` that does
not block when checking stdout or stderr, so that you can poll to see if
there's new output. Class `RestartableProcess` represents an executable that
can be stopped (by killing the underlying process) and restarted
(by re-executing) without invalidating the wrapper object.

`miners.CPUMiner` simply uses `RestartableProcess` to wrap a copy of pooler's
cpuminer, where pausing the miner is implemented as killing the existing process.

`miners.CGMiner` wraps a copy of CGMiner that is started behind the scenes with the remote management API enabled. Pausing is then implemented by reducing the miner's intensity setting to a given "pause intensity" that uses little power, and restarts as setting the intensity back to maximum. This keeps the miner from crashing either itself or the graphics driver, as changes in intensity seems far more stable than process restarts.



