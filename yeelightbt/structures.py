""" This file contains the protocol structures. """
import logging
from construct import (Struct, Int8ub, Int16ub, Const, Padded, Byte, Enum,
                       GreedyBytes, Switch, Pass, this, Probe, Default,
                       Embedded, GreedyString, If, Flag, BytesInteger,
                       SymmetricMapping, Adapter)
import enum

_LOGGER = logging.getLogger(__name__)

# Some help from https://github.com/Marcocanc/node-mi-lamp/blob/master/notes.md

PairingStatus = "status" / Struct(
    "pairing_status" / Enum(Byte,
                            NotPaired=0x01,
                            Paired=0x02,
                            PairedUDID=0x04,
                            Disconnected=0x07)
)

# Name doesn't fit to one element, so there's an index I assume..
# >>> x = bytes.fromhex("43 51 01 00 0d 5965656c696768742042656473")
# >>> x
# b'CQ\x01\x00\rYeelight Beds'
# >>> x = bytes.fromhex("43 51 01 01 08 696465204c616d700000000000")
# >>> x
# b'CQ\x01\x01\x08ide Lamp\x00\x00\x00\x00\x00'

Name = "name" / Struct(
    "part" / Byte,
    "text_part" / GreedyString(),
)


class LampMode(enum.Enum):
    Color = 0x01
    White = 0x02
    Flow = 0x03


class ModeAdapter(Adapter):
    def _encode(self, obj, context):
        return obj.value()

    def _decode(self, obj, context):
        return LampMode(obj)


class ColorAdapter(Adapter):
    def _encode(self, obj, context):
        return {"red": obj["red"],
                "green": obj["green"],
                "blue": obj["blue"],
                "unknown": 0}

    def _decode(self, obj, context):
        return int(obj.red), int(obj.green), int(obj.blue)


Statistics = "stats" / Struct(GreedyBytes)

OnOff = "OnOff" / Struct(
    "state" / SymmetricMapping(Byte, {True: 0x01, False: 0x02}, default=False)
)

Color = "color" / ColorAdapter(Struct(
    "red" / Default(Int8ub, 0),
    "green" / Default(Int8ub, 0),
    "blue" / Default(Int8ub, 0),
    "unknown" / Const(Byte, 0x00)
))

WakeUp = "wakeup" / Struct(
    "time" / Default(Int16ub, 0),
)


# sleep off 30
# 4381 01 1e 0200000000000000000000000000
# sleep on 30
# 4381 01 1e 01 06 fc 0000000000000000000000
# sleep on 15
# 4381 01 0f 01 03 7b 0000000000000000000000
Sleep = "sleep" / Struct(
    "minutes" / Byte,
    "enabled" / Enum(Byte, On=0x01, Off=0x02),
    "unknown" / Byte,
    "unknown2" / Byte,
)

# temperature
# ~6400
# 4343 18fd 0000000000000000000000000000
# ~1832
# 4343 0728 0000000000000000000000000000

# 1700 - 6500 K
Temperature = "temp" / Struct(
    "temperature" / Int16ub,
)

# brightness max
# 4342 64 000000000000000000000000000000
# brightness min
# 4342 01 000000000000000000000000000000
# brightness middle
# 4342 31 000000000000000000000000000000

# 1-100
Brightness = "brightness" / Struct(
    "brightness" / Int8ub,
)

# Night mode query:
# 4370 00000000000000000000000000000000
# Set Night mode on 0000-0500
# 436f 01 01 0000 0500 00000000000000000000
# set night mode off 0000-0500
# 436f 00 01 0000 0500 00000000000000000000
# night mode on response 0000-0500
# 4371 01 01 0000 0500 00000000000000000000
# night mode off
# 4371 00 01 0000 0500 00000000000000000000
# hex is here the real value, so 1800 = 18:00, 0600 = 06:00

NightMode = "nightmode" / Struct(
    "state" / Enum(Byte, Off=0x00, On=0x01),
    "unkn" / Byte,
    "start_time" / BytesInteger(2),
    "end_time" / BytesInteger(2),
)


#      ON MO  R  G  B    BR TEMP
# max brightness:
# 4345 02 01 d6 71 00 00 64 0000 15000000000000
# min brightness:
# 4345 02 01 d6 71 00 00 01 0000 15000000000000
#
# blue max:
# 4345 02 01 00 02 f2 00 64 0000 15000000000000
#
# red max:
# 4345 01 01 f2 01 00 00 64 0000 15000000000000
#
# white, warm:
# 4345 01 02 00 00 00 00 64 078f 15000000000000
#
# white, cold:
# 4345 01 02 00 00 00 00 64 1898 15000000000000

StateResult = Struct(
    "onoff" / Embedded(OnOff),
    "mode" / ModeAdapter(Byte),
    Color,
    Embedded(Brightness),
    Embedded(Temperature),
    "unk" / Byte,
)

Pair = "Pair" / Struct(
    "dev_uid" / Const(Byte, 0x02))

# Note, requests with even, responses with odd

RequestType = "reqtype" / Enum(Byte,
                               SetOnOff=0x40,
                               SetColor=0x41,
                               SetBrightness=0x42,
                               SetTemperature=0x43,
                               GetState=0x44,
                               GetName=0x52,
                               Pair=0x67,
                               SetNightMode=0x6f,
                               GetNightMode=0x70,
                               GetSleepTimer=0x80,
                               GetWakeUp=0x88,
                               GetStatistics=0x8c,
                               )

Request = "msg" / Padded(18, Struct(
    Const(Int8ub, 0x43),
    "type" / RequestType,
    "payload" / Embedded(
        Switch(this.type, {
            "SetOnOff": OnOff,
            "SetColor": Color,
            "SetBrightness": Brightness,
            "SetTemperature": Temperature,
            "Pair": Pair,
        }, default=Pass),
    ),
))

ResponseType = "type" / Enum(Byte,
                             StateResult=0x45,
                             FlowMode=0x4a,
                             SetName=0x51,
                             GetNameResult=0x53,
                             Unknown_5c=0x5c,
                             Status=0x62,
                             PairingResult=0x63,
                             NightModeResult=0x71,
                             SleepTimerResult=0x81,
                             WakeUpResult=0x89,
                             StatisticsResult=0x8d,
                             )

Response = "msg" / Padded(18,
                          Struct(Const(Int8ub, 0x43),
                                 "type" / ResponseType,
                                 # TODO: This flag handling is broken, fix it.
                                 "response" / If(lambda ctx: ctx["type"] != "NightModeResult" and
                                                             ctx["type"] != "PairingResult" and
                                                             ctx["type"] != "StateResult" and
                                                             ctx["type"] != "WakeUpResult", Flag),
                                 "payload" / If(lambda ctx: "response" in ctx,
                                                Embedded(Switch(this.type, {
                                                    "Color": Color,
                                                    "StateResult": StateResult,
                                                    "NightModeResult": NightMode,
                                                    "SetBrightness": Brightness,
                                                    "SetTemperature": Temperature,
                                                    "Temperature": Temperature,
                                                    "SleepTimer": Sleep,
                                                    "SleepTimerResult": Sleep,
                                                    "ReadName": Pass,
                                                    "WakeUpResult": WakeUp,
                                                    "Pair": Pair,
                                                    "PairingResult": PairingStatus,
                                                    "GetNameResult": Name,
                                                }, default=Pass))
                                                )
                                 )
                          )
