"""
A simple wrapper for bluepy's btle.Connection.
Handles Connection duties (reconnecting etc.) transparently.
A butchered version from python-eq3bt, which was butchered from bluepy_devices
with the following license:

The MIT License (MIT)

Copyright (c) 2016 Markus Peter

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
import logging
import codecs
import time

from bluepy import btle

DEFAULT_TIMEOUT = 3

_LOGGER = logging.getLogger(__name__)

class BTLEConnection(btle.DefaultDelegate):
    """Representation of a BTLE Connection."""

    def __init__(self, mac):
        """Initialize the connection."""
        btle.DefaultDelegate.__init__(self)

        self._conn = btle.Peripheral()
        self._conn.withDelegate(self)
        self._mac = mac
        self._callbacks = {}

    def connect(self):
        _LOGGER.debug("Trying to connect to %s", self._mac)
        try:
            self._conn.connect(self._mac)
        except btle.BTLEException as ex:
            _LOGGER.warning("Unable to connect to the device %s, retrying: %s", self._mac, ex)
            try:
                self._conn.connect(self._mac)
            except Exception as ex2:
                _LOGGER.error("Second connection try to %s failed: %s", self._mac, ex2)
                raise

        _LOGGER.debug("Connected to %s", self._mac)

    def disconnect(self):
        if self._conn:
            self._conn.disconnect()
            self._conn = None

    def wait(self, sec):
        end = time.time() + sec
        while time.time() < end:
            self._conn.waitForNotifications(timeout=0.1)

    def get_services(self):
        return self._conn.getServices()

    def get_characteristics(self, uuid=None):
        if uuid:
            _LOGGER.info("Requesting characteristics for uuid %s", uuid)
            return self._conn.getCharacteristics(uuid=uuid)
        return self._conn.getCharacteristics()

    def handleNotification(self, handle, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("Got notification from %s: %s", handle, codecs.encode(data, 'hex'))
        if handle in self._callbacks:
            self._callbacks[handle](data)

    @property
    def mac(self):
        """Return the MAC address of the connected device."""
        return self._mac

    def set_callback(self, handle, function):
        """Set the callback for a Notification handle. It will be called with the parameter data, which is binary."""
        self._callbacks[handle] = function

    def make_request(self, handle, value, timeout=0, with_response=False):
        """Write a GATT Command without callback - not utf-8."""
        _LOGGER.debug("Writing %s to %s with with_response=%s", codecs.encode(value, 'hex'), handle, with_response)
        res = self._conn.writeCharacteristic(handle, value, withResponse=with_response)
        if timeout:
            self.wait(timeout)

        return res

