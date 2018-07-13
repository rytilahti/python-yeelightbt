"""
Yeelight bt platform,
based on demo & yeelight components.

Author: Teemu Rytilahti <tpr@iki.fi>
"""

import logging

import homeassistant.helpers.config_validation as cv

import voluptuous as vol

from homeassistant.const import CONF_DEVICES, CONF_NAME, CONF_MAC

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT,
    ATTR_RGB_COLOR, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_COLOR, SUPPORT_WHITE_VALUE,
    Light, PLATFORM_SCHEMA)

from homeassistant.util.color import (
    color_temperature_mired_to_kelvin as mired_to_kelvin,
    color_temperature_kelvin_to_mired as kelvin_to_mired,
    color_temperature_to_rgb)

CONF_KEEP_ALIVE = "keep_alive"


DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_MAC): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.Schema({cv.string: DEVICE_SCHEMA}),
})

LIGHT_EFFECT_LIST = ['flow', 'none']

SUPPORT_YEELIGHTBT = (SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP |
                      # SUPPORT_EFFECT |
                      SUPPORT_COLOR | SUPPORT_WHITE_VALUE)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the yeelightbt light platform."""
    lights = []
    if discovery_info is not None:
        _LOGGER.debug("Adding autodetected %s", discovery_info['hostname'])

        lights.append(YeelightBT(discovery_info[CONF_MAC], DEVICE_SCHEMA({})))
    else:
        for name, device_cfg in config[CONF_DEVICES].items():
            mac = device_cfg[CONF_MAC]
            lights.append(YeelightBT(name, mac))

    add_devices_callback(lights, True)  # request an update before adding


class YeelightBT(Light):
    """Represenation of a demo light."""

    def __init__(self, name, mac):
        """Initialize the light."""
        self._name = name
        self._mac = mac
        self._state = None
        self._rgb = None
        self._ct = None
        self._brightness = None
        self._effect_list = LIGHT_EFFECT_LIST
        self._effect = 'none'
        self._available = False

        self.__dev = None

    @property
    def available(self):
        return self._available

    @property
    def should_poll(self):
        """No polling needed for a demo light."""
        return True

    @property
    def name(self):
        """Return the name of the light if any."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RBG color value."""
        return self._rgb

    @property
    def color_temp(self):
        """Return the CT color temperature."""
        return self._ct

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_YEELIGHTBT

    @property
    def _dev(self):
        from yeelightbt import Lamp
        if not self.__dev:
            _LOGGER.error("Initializing %s", self._mac)
            self.__dev = Lamp(self._mac, self._status_cb, keep_connection=True)

        return self.__dev

    def _status_cb(self, _):
        _LOGGER.debug("Got notification from the lamp")
        from yeelightbt import LampMode
        if not self._dev.color:
            _LOGGER.error("no color available -> device not connected")
            return  # notification not yet there..
        self._brightness = 255 * (int(self._dev.brightness) / 100)
        self._available = self._dev.available
        self._state = self._dev.is_on
        if self._dev.mode == LampMode.White:
            self._ct = int(kelvin_to_mired(self._dev.temperature))
            # when in white mode, rgb is not set so we calculate it ourselves
            self._rgb = color_temperature_to_rgb(self._dev.temperature)
        else:
            self._ct = 0
            self._rgb = self._dev.color

        _LOGGER.debug("available: %s state: %s rgb: %s ct: %s",
                      self._available, self._state, self._rgb, self._ct)

        self.update_ha_state()

    def update(self):
        # Note, update should only start fetching,
        # followed by asynchronous updates through notifications.
        with self._dev:
            self._dev.state()

    def turn_on(self, **kwargs):
        """Turn the light on."""
        self._state = True
        with self._dev:
            if ATTR_RGB_COLOR in kwargs:
                rgb = kwargs[ATTR_RGB_COLOR]
                self._rgb = rgb
                self._dev.set_color(rgb[0], rgb[1], rgb[2])

            if ATTR_COLOR_TEMP in kwargs:
                mireds = kwargs[ATTR_COLOR_TEMP]
                temp_in_k = mired_to_kelvin(mireds)
                self._dev.set_temperature(int(temp_in_k))
                self._ct = mireds

            if ATTR_BRIGHTNESS in kwargs:
                brightness = kwargs[ATTR_BRIGHTNESS]
                self._dev.set_brightness(int(brightness / 255 * 100))
                self._brightness = brightness

            # if we are just started without parameters, turn on.
            if ATTR_RGB_COLOR not in kwargs and \
               ATTR_COLOR_TEMP not in kwargs and \
               ATTR_BRIGHTNESS not in kwargs:
                self._dev.turn_on()

        # if ATTR_EFFECT in kwargs:
        #    self._effect = kwargs[ATTR_EFFECT]

    def turn_off(self, **kwargs):
        """Turn the light off."""
        with self._dev:
            self._dev.turn_off()
            self._state = False
