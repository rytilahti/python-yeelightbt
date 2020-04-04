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

# Home Assistant support

This repository also contains a basic [Home Assistant](https://home-assistant.io/) custom component.

## Yeelightbt installation on Home Assistant (for Raspberry Pi)

1) SSH into the host through port 22222 to get all necessary privileges (follow setup [there](https://developers.home-assistant.io/docs/hassio_debugging/)).  /!\ Using the SSH add-on will not work, it gives access to port 22. Use Putty for instance: 
```
ssh root@192.168.XX.XX -p 22222
```
You will be logged into the Home Assistant command line interface and type `login` to access the host system.
 
 2) Access the bash:
```
docker exec -it $(docker ps -f name=homeassistant -q) bash
```

3) Yeelightbt requires bluepy and the installer may not find where it is located. Therefore, navigate to the package:
```
cd /usr/local/lib/python3.7/site-packages/bluepy
```

4) Install as mentionned above:
```
pip install git+https://github.com/rytilahti/python-yeelightbt/
```

5) Ensure the light is ON and the switch is on the bluetooth position (at least for the Candela). Detect the supported devices and check if the lamp can be turned on/off with the commands described above.

## Custom Component Installation

Copy `yeelight_bt` directory located under `custom_components` over to `~/.homeassistant/custom_components/`.

## Configuration

```
light:
  - platform: yeelight_bt
    devices:
      Bedside:
        mac: 'f8:24:41:xx:xx:xx'
```

## Limitation
With the current custom component version, Home Assistant may lose the connection with the devices after a few minutes or hours. Home Assistant has to be restarted to reestablish this connection
