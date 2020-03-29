# Python library for Yeelight Bedside lamp

This library allows controlling Yeelight's bluetooth-enabled [bedside lamp](http://www.yeelight.com/en_US/product/yeelight-ctd) and [Candela](https://www.yeelight.com/en_US/product/gingko) devices.

**Note that this library is not actively maintained, however, patches are very welcome.**

Candelas support only setting the light on and off, and adjusting the brightness.

Currently supported features:
* State
* Color mode (white, color, flow)
* Temperature
* Brightness
* Sleep, wakeup & scheduling (partially)

# Installation

```
pip install git+https://github.com/rytilahti/python-yeelightbt/
```

In case you are getting "No such file or directory" error for bluepy-helper, you have to go into bluepy's directory and run make there.
It is also a good idea to let the helper to have capabilities for accessing the bluetooth devices without being root, e.g., by doing the following:

```
setcap cap_net_admin,cap_net_raw+eip bluepy-helper
```

And then simply try if the scanning works. You can use pass '-dd' as option to the command to see the debug messages from bluepy in case it is not working.

# Usage

Try
```
$ yeelightbt --help
```
and
```
$ yeelightbt [command] --help
```

For debugging you can pass -d/--debug, adding it second time will also print out the debug from bluepy.

## Finding supported devices

```
$ yeelightbt scan
Scanning for 5 seconds
Devices found:
  f8:24:41:xx:xx:xx (XMCTD_XXXX), rssi=-83

```

## Reading status & states

To avoid passing ```--mac``` for every call, set the following environment variable:

```
export YEELIGHTBT_MAC=AA:BB:CC:11:22:33
```

```
$ yeelightbt

MAC: f8:24:41:xx:xx:xx
  Mode: LampMode.White
  Color: (0, 0, 0)
  Temperature: 5000
  Brightness: 50
```

```
$ yeelightbt temperature

Temperature: 5000
```

```
$ yeelightbt color 255 0 0
Setting color: 255 0 0
```

# Homeassistant support

This repository also contains a basic [Home Assistant](https://home-assistant.io/) custom component.


## Manual Installation

Just copy `yeelight_bt` directory located under `custom_components` over to `~/.homeassistant/custom_components/`.

## Configuration

```
light:
  - platform: yeelight_bt
    devices:
      Bedside:
        mac: 'f8:24:41:xx:xx:xx'
```
