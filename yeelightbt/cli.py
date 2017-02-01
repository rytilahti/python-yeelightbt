import logging
from yeelightbt import Lamp
from bluepy import btle
import click

# To allow callback debugs, just pass --debug to the tool
DEBUG = 0

pass_dev = click.make_pass_decorator(Lamp)


@click.pass_context
def paired_cb(ctx, data):
    if DEBUG:
        click.echo("Got paired? %s" % data.pairing_status)


@click.pass_context
def notification_cb(ctx, data):
    if DEBUG:
        click.echo("Got notification: %s" % data)


@click.group(invoke_without_command=True)
@click.option('--mac', envvar="YEELIGHTBT_MAC", required=True)
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

    lamp = Lamp(mac, notification_cb, paired_cb,
                keep_connection=True, wait_after_call=0.5)
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
    devs = scan.scan(sec)
    click.echo("Devices found:")
    for dev in devs:
        localname = dev.getValueText(9)
        if localname and localname.startswith("XMCTD_"):
            click.echo("  %s (%s), rssi=%d" % (dev.addr, localname, dev.rssi))


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
@pass_dev
def color(dev, red, green, blue):
    """ Gets or sets the color. """
    if red or green or blue:
        click.echo("Setting color: %s %s %s" % (red, green, blue))
        dev.set_color(red, green, blue)
    else:
        click.echo("Color: %s" % (dev.color,))


@cli.command()
@pass_dev
def state(dev):
    """ Requests the state from the device. """
    click.echo("MAC: %s" % dev.mac)
    click.echo("  Mode: %s" % dev.mode)
    click.echo("  Color: %s" % (dev.color,))
    click.echo("  Temperature: %s" % dev.temperature)
    click.echo("  Brightness: %s" % dev.brightness)


@cli.command()
@click.argument('temperature', type=int, default=None, required=False)
@pass_dev
def temperature(dev, temperature):
    """ Gets and sets the color temperature 1700-6500K """
    if temperature:
        click.echo("Setting the temperature to %s" % temperature)
        dev.set_temperature(temperature)
    else:
        click.echo("Temperature: %s" % dev.temperature)


if __name__ == "__main__":
    cli()
