import struct
import codecs
import logging
from .connection import BTLEConnection
from .structures import Request, Response

_LOGGER = logging.getLogger(__name__)


def cmd(cmd):
    def _wrap(self, *args, **kwargs):
        req = cmd(self, *args, **kwargs)

        params = None
        wait = self._wait_after_call
        if isinstance(req, tuple):
            params = req[1]
            req = req[0]

        query = {"type": req}
        if params:
            if "wait" in params:
                wait = params["wait"]
                del params["wait"]
            query.update(params)

        _LOGGER.debug(">> %s (wait: %s)", query, wait)
        _ex = None
        try_count = 3
        while try_count > 0:
            try:
                res = self._conn.make_request(self.WRITE_HANDLE,
                                              Request.build(query),
                                              timeout=wait)
                return res
            except Exception as ex:
                _LOGGER.error("got exception, tries left %s: %s",
                              try_count, ex)
                _ex = ex
                try_count -= 1
                self.connect()
                continue
        raise _ex

    return _wrap


class Lamp:
    NOTIFY_HANDLE = 0x15
    REGISTER_NOTIFY_HANDLE = 0x16
    WRITE_HANDLE = 0x12
    NOTIFY_UUID = "8f65073d-9f57-4aaa-afea-397d19d5bbeb"
    CONTROL_UUID = "aa7d3f34-2d4f-41e0-807f-52fbf8cf7443"

    def __init__(self, mac, status_cb=None, paired_cb=None,
                 keep_connection=False, wait_after_call=0):
        self._mac = mac
        self._is_on = False
        self._brightness = None
        self._temperature = None
        self._rgb = None
        self._mode = None
        self._paired_cb = paired_cb
        self._status_cb = status_cb
        self._keep_connection = keep_connection
        self._wait_after_call = wait_after_call
        import threading
        self._lock = threading.RLock()
        self._conn = None

    @property
    def mac(self):
        return self._mac

    @property
    def available(self):
        return self._mode is not None

    @property
    def mode(self):
        return self._mode

    def connect(self):
        if self._conn:
            self._conn.disconnect()
        self._conn = BTLEConnection(self._mac)
        self._conn.set_callback(self.NOTIFY_HANDLE, self.handle_notification)
        self._conn.connect()
        # We need to register to receive notifications
        self._conn.make_request(self.REGISTER_NOTIFY_HANDLE,
                                struct.pack("<BB", 0x01, 0x00),
                                timeout=None)
        self.pair()

    def disconnect(self):
        self._conn.disconnect()

    def __enter__(self):
        self._lock.acquire()
        if not self._conn and self._keep_connection:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()
        if not self._keep_connection:
            _LOGGER.info("not keeping the connection, disconnecting..")
            self._conn.disconnect()

        return

    @cmd
    def pair(self):
        return "Pair"

    def wait(self, sec):
        self._conn.wait(sec)

    @property
    def is_on(self):
        return self._is_on

    @cmd
    def turn_on(self):
        return "SetOnOff", {"state": True}

    @cmd
    def turn_off(self):
        return "SetOnOff", {"state": False}

    @cmd
    def get_name(self):
        return "GetName"

    @cmd
    def get_statistics(self):
        return "GetStatistics"

    @cmd
    def get_wakeup(self):
        return "GetWakeUp"

    @cmd
    def get_night_mode(self):
        return "GetNightMode"

    @cmd
    def get_sleep_timer(self):
        return "GetSleepTimer"

    @property
    def temperature(self):
        return self._temperature

    @cmd
    def set_temperature(self, kelvin):
        return "SetTemperature", {"temperature": kelvin}

    @property
    def brightness(self):
        return self._brightness

    @cmd
    def set_brightness(self, brightness):
        return "SetBrightness", {"brightness": brightness}

    @property
    def color(self):
        return self._rgb

    @cmd
    def set_color(self, red, green, blue):
        return "SetColor", {"red": red, "green": green, "blue": blue}

    @cmd
    def state(self):
        return "GetState"

    def __str__(self):
        return "<Lamp %s is_on(%s) mode(%s) rgb(%s) brightness(%s) colortemp(%s)>" % (
            self._mac, self._is_on, self._mode, self._rgb, self._brightness, self._temperature)

    def handle_notification(self, data):
        _LOGGER.debug("<< %s", codecs.encode(data, 'hex'))
        res = Response.parse(data)
        if res.type == "StateResult":
            self._is_on = res.payload.state
            self._mode = res.payload.mode
            self._rgb = res.payload.color
            self._brightness = res.payload.brightness
            self._temperature = res.payload.temperature

            if self._status_cb:
                self._status_cb(self)
        elif res.type == "PairingResult":
            _LOGGER.debug("pairing res: %s", res)

            if self._paired_cb:
                self._paired_cb(res.payload)

        else:
            _LOGGER.info("Unhandled cb: %s", res)
