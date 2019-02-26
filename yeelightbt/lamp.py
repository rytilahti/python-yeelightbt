import struct
import codecs
import logging
import time
import threading
from .connection import BTLEConnection
from .structures import Request, Response, StateResult

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
            query["payload"] = params

        _LOGGER.debug(">> %s (wait: %s)", query, wait)
        _ex = None
        try_count = 3
        while try_count > 0:
            try:
                request_bytes = Request.build(query)
                res = self.control_char.write(request_bytes,
                                              withResponse=True)
                self._conn.wait(wait)

                return res
            except Exception as ex:
                _LOGGER.error("got exception on %s, tries left %s: %s",
                              query, try_count, ex)
                raise
                _ex = ex
                try_count -= 1
                self.connect()
                continue
        raise _ex

    return _wrap


class Lamp:
    REGISTER_NOTIFY_HANDLE = 0x16
    MAIN_UUID =   "8e2f0cbd-1a66-4b53-ace6-b494e25f87bd"
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
        self._conn.connect()

        notify_char = self._conn.get_characteristics(Lamp.NOTIFY_UUID)
        self.notify_handle = notify_char.pop().getHandle()
        _LOGGER.debug("got notify handle: %s" % self.notify_handle)
        self._conn.set_callback(self.notify_handle, self.handle_notification)

        control_chars = self._conn.get_characteristics(Lamp.CONTROL_UUID)
        self.control_char = control_chars.pop()
        self.control_handle = self.control_char.getHandle()
        _LOGGER.debug("got control handle: %s" % self.control_handle)

        # We need to register to receive notifications
        self._conn.make_request(self.REGISTER_NOTIFY_HANDLE,
                                struct.pack("<BB", 0x01, 0x00),
                                timeout=None)
        self.pair()

    def wait_for_notifications(self):
        while True:
            self._conn.wait(1)

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
        end = time.time() + sec
        while time.time() < end:
            self._conn.wait(0.1)

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
        return "GetName", {"wait": 0.5}

    @cmd
    def get_scene(self, scene_id):
        return "GetScene", {"id": scene_id}

    @cmd
    def set_scene(self, scene_id, scene_name):
        return "SetScene", {"scene_id": scene_id, "text": scene_name}

    @cmd
    def get_version_info(self):
        return "GetVersion"

    @cmd
    def get_serial_number(self):
        return "GetSerialNumber"

    @cmd
    def get_time(self):
        return "GetTime"

    @cmd
    def set_time(self, new_time):
        return "SetTime", {"time": new_time}

    @cmd
    def get_nightmode(self):
        return "GetNightMode"

    @cmd
    def get_statistics(self):
        return "GetStatistics"

    @cmd
    def get_wakeup(self):
        return "GetWakeUp"

    @cmd
    def get_night_mode(self):
        return "GetNightMode"

    @property
    def temperature(self):
        return self._temperature

    @cmd
    def set_temperature(self, kelvin: int, brightness: int):
        return "SetTemperature", {"temperature": kelvin, "brightness": brightness}

    @property
    def brightness(self):
        return self._brightness

    @cmd
    def set_brightness(self, brightness: int):
        return "SetBrightness", {"brightness": brightness}

    @property
    def color(self):
        return self._rgb

    @cmd
    def set_color(self, red: int, green: int, blue: int, brightness: int):
        return "SetColor", {"red": red, "green": green, "blue": blue, "brightness": brightness}

    @cmd
    def state(self) -> StateResult:
        return "GetState", {"wait": 0.5}

    @cmd
    def get_alarm(self, number):
        return "GetAlarm", {"id": number, "wait": 0.5}

    @cmd
    def get_flow(self, number):
        return "GetSimpleFlow", {"id": number, "wait": 0.5}

    @cmd
    def get_sleep(self):
        return "GetSleepTimer", {"wait": 0.5}

    def __str__(self):
        return "<Lamp %s is_on(%s) mode(%s) rgb(%s) brightness(%s) colortemp(%s)>" % (
            self._mac, self._is_on, self._mode, self._rgb, self._brightness, self._temperature)

    def handle_notification(self, data):
        _LOGGER.debug("<< %s", codecs.encode(data, 'hex'))
        res = Response.parse(data)
        payload = res.payload
        if res.type == "StateResult":
            self._is_on = payload.state
            self._mode = payload.mode
            self._rgb = (payload.red, payload.green, payload.blue, payload.white)
            self._brightness = payload.brightness
            self._temperature = payload.temperature

            if self._status_cb:
                self._status_cb(self)
        elif res.type == "PairingResult":
            _LOGGER.debug("pairing res: %s", res)

            if self._paired_cb:
                self._paired_cb(res)

        else:
            _LOGGER.info("Unhandled cb: %s", res)
