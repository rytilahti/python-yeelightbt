""" This file contains the protocol structures. """
import logging
import datetime
from construct import (
    Bytes, GreedyBytes, Byte, Int16ub, Byte, BytesInteger, PascalString, 
    Enum, FlagsEnum, Flag, Mapping, Int8ub,
    Struct, Embedded, EmbeddedSwitch, Const, Padded, If, Switch, 
    Pass, Default, Seek, Adapter, ExprAdapter, this, Probe)

_LOGGER = logging.getLogger(__name__)

# Some help from https://github.com/Marcocanc/node-mi-lamp/blob/master/notes.md

PairingStatus = Struct(
    "pairing_status" / Enum(Byte,
        PairRequest=0x01,
        PairSuccess=0x02,
        PairFailed=0x03,
        PairedDevice=0x04,
        UnknownState=0x06,
        Disconnected=0x07,
        # not documented?
    ),
)

# Name doesn't fit to one element, so there's an index I assume..
# >>> x = bytes.fromhex("43 51 01 00 0d 5965656c696768742042656473")
# >>> x
# b'CQ\x01\x00\rYeelight Beds'
# >>> x = bytes.fromhex("43 51 01 01 08 696465204c616d700000000000")
# >>> x
# b'CQ\x01\x01\x08ide Lamp\x00\x00\x00\x00\x00'

Name = Struct(
    "id" / Byte,
    "index" / Byte, # convert greeedystring to use this
    "text" / PascalString(Byte, "ascii"),
)

Version = Struct(
    "currentrunning" / Enum(Byte, App1=0x01, App2=0x02, Candela=0x31),
    "hw_version" / Int16ub,
    "sw_version_app1" / Int16ub,
    "sw_version_app2" / Int16ub,
    "beacon_version" / Int16ub,
)

SerialNumber = Struct(
    "serialno" / BytesInteger(12),
)


# REVIEW: Enum34 module should not be used unless absolutely necessary.
# For equality use (parsed value) == LampMode.Color (its a string value).
# If integer value is not mapped, parsing returns an integer not string.
#
# YOU NEED TO ADJUST OTHER CODE THAT USES THIS FIELD ALSO.
#
LampMode = Enum(Byte, 
    Color = 0x01,
    White = 0x02,
    Flow = 0x03,
)


class TimeAdapter(Adapter):
    def _decode(self, obj, context, path):
        return datetime.datetime(
            year=obj.year+2000, month=obj.month, day=obj.day,
            hour=obj.hour, minute=obj.minute, second=obj.second,
        )

    def _encode(self, obj, context, path):
        return dict(
            year=obj.year-2000, month=obj.month, day=obj.day,
            hour=obj.hour, minute=obj.minute, second=obj.second,
            dow=obj.weekday(),
        )


class HourMinuteAdapter(Adapter):
    """Converts 0x12 0x00 to 12:00 and otherway around."""
    # REVIEW: this adapter is used with 2 different structs, only one has second field
    def _decode(self, obj, context, path):
        return datetime.time(
            hour=obj.hour, minute=obj.minute, second=obj.get('second', 0),
        )
    # REVIEW: value 'second' was missing, would not build?
    def _encode(self, obj, context, path):
        return dict(
            hour=obj.hour, minute=obj.minute, second=obj.second,
        )


class RawAsInt(Adapter):
    """Formats given byte's hex value as int."""
    def _decode(self, obj, context, path):
        return int('{:02x}'.format(obj))

    def _encode(self, obj, context, path):
        # REVIEW: return was missing?
        return bytearray.fromhex(str(obj).zfill(2))


Time = Struct(
    "time" / TimeAdapter(Struct(
        "second" / RawAsInt(Byte),
        "minute" / RawAsInt(Byte),
        "hour" / RawAsInt(Byte),
        "day" / RawAsInt(Byte),
        "dow" / RawAsInt(Byte),
        "month" / RawAsInt(Byte),
        "year" / RawAsInt(Byte),
    )),
)

HourMinute = Struct(
    "time" / HourMinuteAdapter(Struct(
        "hour" / RawAsInt(Byte),
        "minute" / RawAsInt(Byte),
    )),
)

HourMinuteSecond = Struct(
    "time" / HourMinuteAdapter(Struct(
        "hour" / RawAsInt(Byte),
        "minute" / RawAsInt(Byte),
        "second" / RawAsInt(Byte),
    )),
)

# REVIEW: This field should be named if you dont want to discard the parsed value,
# and also to allow building it.
Statistics = Struct(
    GreedyBytes,
)

# REVIEW: previously this had default=False, current code would fail on other values.
# If you need those, use an Adapter to convert between booleans-integers.
OnOff = Struct(
    "state" / Mapping(Byte, {True: 0x01, False: 0x02})
)

RGB = Struct(
    "red" / Default(Byte, 0),
    "green" / Default(Byte, 0),
    "blue" / Default(Byte, 0),
)

Color = Struct(
    Embedded(RGB),
    "white" / Default(Byte, 0),
    "brightness" / Default(Byte, 0),
)

WeekDayEnum = FlagsEnum(Byte, sun=0x01, mon=0x02, tue=0x04, wed=0x08, thu=0x10, fri=0x20, sat=0x40)

Alarm = Struct(
    "id" / Byte, # 1-6, 6 = wake up fall sleep mode, ff = end of list
    Embedded(HourMinuteSecond),
    "mode" / Enum(Byte, Single=0x01, RepeatDaily=0x02, RepeatOnDays=0x03),
    "days" / Switch(this.mode, 
        {
            "Single": RawAsInt(Byte), # date in BCD
            "RepeatDaily": Byte,
            "RepeatOnDays": WeekDayEnum,
        },
        default=Byte,
    ),
    "gradual_change" / Int16ub,
    "action" / Enum(Byte, Sunrise=0x01, Sunset=0x02, On=0x03, Off=0x04),
    "sync_phone" / Enum(Byte, Off=0x00, On=0x01),
    "enabled" / Enum(Byte, Off=0x00, On=0x01),
)

WakeUp = Struct(
    "time" / Default(Int16ub, 0),
)


SetSleep = Struct(
    "control" / Enum(Byte, Enable=0x01, Disable=0x02, Start=0x03, Stop=0x04),
    "time" / Byte,
)

# sleep off 30
# 4381 01 1e 0200000000000000000000000000
# sleep on 30
# 4381 01 1e 01 06 fc 0000000000000000000000
# sleep on 15
# 4381 01 0f 01 03 7b 0000000000000000000000
SleepTimerResult = Struct(
    "enabled" / Enum(Byte, On=0x01, Off=0x02),
    "minutes" / Byte,
    "state" / Enum(Byte, Unknown=0, On=1, Off=2, Candela=15),
    "left_time" / Int16ub,
)

# temperature
# ~6400
# 4343 18fd 0000000000000000000000000000
# ~1832
# 4343 0728 0000000000000000000000000000

# 1700 - 6500 K
Temperature = Struct(
    "temperature" / Int16ub,
    "brightness" / Default(Byte, 255), # 1-100, invalids ignored
)

# brightness max
# 4342 64 000000000000000000000000000000
# brightness min
# 4342 01 000000000000000000000000000000
# brightness middle
# 4342 31 000000000000000000000000000000

# 1-100
Brightness = Struct(
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

NightMode = Struct(
    "state" / Enum(Byte, Off=0x00, On=0x01),
    "brightness" / Byte,
    "start" / HourMinute,
    "end" / HourMinute,
)

ColorFlow = Struct(
    "id" / Byte, # 1-5 scene, 6 for what?
    "pkt_num" / Byte,
    "cmd" / Byte, # 1 start, 2 set, 3 stop, 4 store
    "rgb_mode" / Byte, # 0 scene, 1 rgbb, 2 color temp
    Embedded(Color),
    Embedded(Temperature),
    "time" / Int16ub, # time range 0-600s
)

# TODO fixme incomplete, instead of RGB it should be temperature on two bytes when mode = temperature
SimpleFlow = Struct(
    "id" / Byte, # 1-5 scene, 6?
    "type" / Enum(Byte, Color=0x01, Temperature=0x02),
    "time" / Byte, # 0-255
    "control" / Byte,
    "first" / RGB,
    "second" / RGB,
    "third" / RGB,
    "fourth" / RGB,
)

Scene = "scene" / Struct(
    "scene_id" / Byte, # 1-5
    "idx" / Default(Byte, 0),
    "text" / PascalString(Byte, 'ascii'),
)

#      ON MO  R  G  B    BR TEMP
# max brightness:
# 4345 02 01 d6 71 00 00 64 0000 15000000000000
# white, warm:
# 4345 01 02 00 00 00 00 64 078f 15000000000000

StateResult = Struct(
    Embedded(OnOff),
    "mode" / LampMode,
    Embedded(Color),
    "temperature" / Int16ub, #, as Temeprature contains brightness.
    "temp_fraction" / Default(Byte, 0),
)

# Using hardcoded devid, this may or may not work if you try to use different
# bluetooth adapters (or devices) to control the same light.
Pair = Struct(
    "devid" / Default(Bytes(16), 0x1234),
)

# Note, requests with (mostly) even, responses with odd
RequestType = Enum(Byte,
    SetOnOff=0x40,
    SetColor=0x41,
    SetBrightness=0x42,
    SetTemperature=0x43,
    GetState=0x44,
    SetAlarm=0x46,
    GetAlarm=0x47,
    DeleteAlarm=0x48,
    SetFlow=0x4a,
    SetFlowTimerBrightness=0x4b,
    GetFlow=0x4b,
    Candela_unknown=0x4c,
    SetScene=0x4e,
    GetScene=0x4f,
    GetName=0x52,
    EnableBeacon=0x54,
    AddBeacon=0x55,
    DeleteBeacon=0x56,
    GetBeacon=0x57,
    SetGradual=0x59,
    GetGradual=0x5a,
    GetVersion=0x5c,
    GetSerialNumber=0x5e,
    SetTime=0x60,
    GetTime=0x61,
    Pair=0x67,
    SetNightMode=0x6f,
    GetNightMode=0x70,
    DeleteScene=0x73,
    FactoryReset=0x74,
    TestMode=0x75,
    SetSimpleFlow=0x7c,
    GetSimpleFlow=0x7d,
    SimpleFlowResult=0x7e,
    SetSleepTimer=0x7f,
    GetSleepTimer=0x80,
    SetWakeUp=0x88,
    GetWakeUp=0x89,
    GetStatistics=0x8c, # for testing only
    Candela_A2=0xa2,
    Candela_A3=0xa3,
    Candela_A4=0xa4,
)

Request = Padded(18,
    Struct(
        Const(0x43, Byte),
        "type" / RequestType,
        "payload" / Switch(
        this.type,
        {
            "SetOnOff": Default(OnOff, Pass),
            "SetColor": Default(Color, Pass),
            "SetBrightness": Default(Brightness, Pass),
            "SetTemperature": Default(Temperature, Pass),
            "Pair": Pair,
            "GetAlarm": Default(Struct("id" / Byte), Pass), # 1-6, 255
            "GetScene": Default(Struct("id" / Byte), Pass), # 1-6, 255
            "GetSimpleFlow": Default(Struct("id" / Byte), Pass),
            "SetScene": Default(Scene, Pass),
        }
        ),
    )
)

ResponseType = Enum(Byte,
    StateResult=0x45,
    AlarmResult=0x49,
    FlowMode=0x4a,
    FlowInfo=0x4d,
    SceneResult=0x50,
    SetName=0x51,
    GetNameResult=0x53,
    BeaconResult=0x58,
    GradualResult=0x5b,
    VersionResult=0x5d,
    SerialNumberResult=0x5f,
    TimeResult=0x62,
    PairingResult=0x63,
    NightModeResult=0x71,
    SimpleFlowResult=0x73,
    SleepTimerResult=0x81,
    #WakeUpResult=0x89,
    WakeUpResult=0x8a,
    StatisticsResult=0x8d,
)

Response = Padded(18,
    Struct(
        Const(0x43, Byte),
        "type" / ResponseType,
        "payload" / Switch(
            this.type,
            {
                "Color": Color,
                "StateResult": StateResult,
                "AlarmResult": Alarm,
                "SceneResult": Scene,
                "NightModeResult": NightMode,
                "SetBrightness": Brightness,
                "SetTemperature": Temperature,
                "Temperature": Temperature,
                "SleepTimerResult": SleepTimerResult,
                "VersionResult": Version,
                "SerialNumberResult": SerialNumber,
                "WakeUpResult": Alarm,
                "TimeResult": Time,
                "SimpleFlowResult": SimpleFlow,
                "Pair": Pair,
                "PairingResult": PairingStatus,
                "GetNameResult": Name,
            }
        )
    )
)