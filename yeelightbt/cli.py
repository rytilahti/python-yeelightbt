import logging
from yeelightbt import Lamp
from bluepy import btle
import click
import sys
import time

# To allow callback debugs, just pass --debug to the tool
DEBUG = 0

pass_dev = click.make_pass_decorator(Lamp)


@click.pass_context
def paired_cb(ctx, data):
    data = data.payload
    if data.pairing_status == "PairRequest":
        click.echo("Waiting for pairing, please push the button/change the brightness")
        time.sleep(5)
    elif data.pairing_status == "PairSuccess":
        click.echo("We are paired.")
    elif data.pairing_status == "PairFailed":
        click.echo("Pairing failed, exiting")
        sys.exit(-1)
    if DEBUG:
        click.echo("Got paired? %s" % data.pairing_status)


@click.pass_context
def notification_cb(ctx, data):
    print("Got notif: %s" % data)
    if DEBUG:
        click.echo("Got notification: %s" % data)


@click.group(invoke_without_command=True)
@click.option('--mac', envvar="YEELIGHTBT_MAC", required=False)
@click.option('-d', '--debug', default=False, count=True)
@click.pass_context
def cli(ctx, mac, debug):
    """ A tool to query Yeelight bedside lamp. """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        if debug > 1:
            btle.Debugging = True
        DEBUG = debug
    else:
        logging.basicConfig(level=logging.INFO)

    # if we are scanning, we do not try to connect.
    if ctx.invoked_subcommand == "scan":
        return

    if mac is None:
        logging.error("You have to specify MAC address to use either by setting YEELIGHTBT_MAC environment variable or passing --mac option!")
        sys.exit(1)

    lamp = Lamp(mac, notification_cb, paired_cb,
                keep_connection=True, wait_after_call=0.2)
    lamp.connect()
    lamp.state()
    ctx.obj = lamp

    if ctx.invoked_subcommand is None:
        ctx.invoke(state)

@cli.command()
def scan():
    """ Scans for available devices. """
    scan = btle.Scanner()
    sec = 5
    click.echo("Scanning for %s seconds" % sec)
    try:
        devs = scan.scan(sec)
    except btle.BTLEException as ex:
        logging.error("Unable to scan for devices, did you set-up permissions for bluepy-helper correctly? ex: %s" % ex)
        return

    click.echo("Devices found:")
    for dev in devs:
        localname = dev.getValueText(9)
        if not localname: continue
        if localname.startswith("XMCTD_"):
            click.echo("Bedlight lamp v1  %s (%s), rssi=%d" % (dev.addr, localname, dev.rssi))
        elif localname.startswith("yeelight_ms"):
            click.echo("Candela %s (%s), rssi=%d" % (dev.addr, localname, dev.rssi))

@cli.command()
@pass_dev
def device_info(dev):
    """Returns hw & sw version."""
    vers = dev.get_version_info()
    serial = dev.get_serial_number()

@cli.command(name="time")
@click.argument("new_time", default=None, required=False)
@pass_dev
def time_(dev, new_time):
    """Gets or sets the time."""
    if new_time:
        click.echo("Setting the time to %s" % new_time)
        dev.set_time(new_time)
    else:
        click.echo("Requesting time.")
        dev.get_time()

@cli.command()
@pass_dev
def on(dev):
    """ Turns the lamp on. """
    dev.turn_on()


@cli.command()
@pass_dev
def off(dev):
    """ Turns the lamp off. """
    dev.turn_off()

@cli.command()
@pass_dev
def wait_for_notifications(dev):
    """Wait for notifications."""
    dev.wait_for_notifications()

@cli.command()
@click.argument("brightness", type=int, default=None, required=False)
@pass_dev
def brightness(dev, brightness):
    """ Gets or sets the brightness. """
    if brightness:
        click.echo("Setting brightness to %s" % brightness)
        dev.set_brightness(brightness)
    else:
        click.echo("Brightness: %s" % dev.brightness)


@cli.command()
@click.argument("red", type=int, default=None, required=False)
@click.argument("green", type=int, default=None, required=False)
@click.argument("blue", type=int, default=None, required=False)
@click.argument("brightness", type=int, default=None, required=False)
@pass_dev
def color(dev, red, green, blue, brightness):
    """ Gets or sets the color. """
    if red or green or blue:
        click.echo("Setting color: %s %s %s (brightness: %s)" % (red, green, blue, brightness))
        dev.set_color(red, green, blue, brightness)
    else:
        click.echo("Color: %s" % (dev.color,))

@cli.command()
@pass_dev
def name(dev):
    dev.get_name()

@cli.command()
@click.argument("number", type=int, default=255, required=False)
@click.argument("name", type=str, required=False)
@pass_dev
def scene(dev, number, name):
    if name:
        dev.set_scene(number, name)
    else:
        dev.get_scene(number)

@cli.command()
@click.argument("number", type=int, default=255, required=False)
@pass_dev
def alarm(dev, number):
    """Gets alarms."""
    dev.get_alarm(number)

@cli.command()
@pass_dev
def night_mode(dev):
    """Gets or sets night mode settings."""
    dev.get_nightmode()

@cli.command()
@click.argument("number", type=int, default=255, required=False)
@pass_dev
def flow(dev, number):
    dev.get_flow(number)

@cli.command()
@click.argument("time", type=int, default=0, required=False)
@pass_dev
def sleep(dev: Lamp, time):
    dev.get_sleep()

@cli.command()
@pass_dev
def state(dev):
    """ Requests the state from the device. """
    click.echo(click.style("MAC: %s" % dev.mac, bold=dev.is_on))
    click.echo("  Mode: %s" % dev.mode)
    click.echo("  Color: %s" % (dev.color,))
    click.echo("  Temperature: %s" % dev.temperature)
    click.echo("  Brightness: %s" % dev.brightness)

    dev._conn.wait(60)


@cli.command()
@click.argument('temperature', type=int, default=None, required=False)
@click.argument('brightness', type=int, default=None, required=False)
@pass_dev
def temperature(dev, temperature, brightness):
    """ Gets and sets the color temperature 1700-6500K """
    if temperature:
        click.echo("Setting the temperature to %s (brightness: %s)" % (temperature, brightness))
        dev.set_temperature(temperature, brightness)
    else:
        click.echo("Temperature: %s" % dev.temperature)


if __name__ == "__main__":
    cli()
