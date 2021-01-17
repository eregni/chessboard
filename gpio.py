#!/usr/bin/env python3
"""Gpio with pigpio and spidev module"""

from time import sleep
import logging
import RPi.GPIO as GPIO
import spidev
import config
from typing import Union, List, Tuple, Callable

LOG = logging.getLogger(__name__)

# Pins
RST_PIN = config.RST_PIN
DC_PIN = config.DC_PIN
CS_EPAPER_PIN = config.CS_EPAPER_PIN
BUSY_PIN = config.BUSY_PIN
CS_BUTTON_PIN = config.CS_BUTTON_PIN

# mcp23017 registers
MCP_READ = 0x41
MCP_WRITE = 0x40

IOCON = 0x0A
IODIRA = 0x00
IODIRB = 0x01
IPOLA = 0x02
IPOLB = 0x03
GPINTENA = 0x04
GPINTENB = 0x05
DEFVALA = 0x06
DEFVALB = 0x07
INTCONA = 0x08
INTCONB = 0x09
GPPUA = 0x0C
GPPUB = 0x0D
INTFA = 0x0E
INTFB = 0x0F
INTCAPA = 0x10
INTCAPB = 0x11
GPIOA = 0x12
GPIOB = 0x13
OLATA = 0x14
OLATB = 0x15

SPI_EPAPER = spidev.SpiDev()
SPI_BUTTONS = spidev.SpiDev()


def init():
    """Initialize gpio stuff"""
    init_gpio()
    init_buttons()
    init_epaper()


def init_gpio():
    """init other gpio pins"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # Arduino interrupt
    GPIO.setup(config.ARDUINO_INT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def init_buttons():
    """init spi device for buttons"""
    GPIO.setup(config.BUTTON_RESET_PIN, GPIO.OUT)
    GPIO.output(config.BUTTON_RESET_PIN, GPIO.HIGH)
    GPIO.setup(config.CS_BUTTON_PIN, GPIO.OUT)
    SPI_BUTTONS.open(0, 0)
    SPI_BUTTONS.max_speed_hz = 8000000
    SPI_BUTTONS.mode = 0
    # mcp23S17 config
    button_reset()
    mcp23s17_read_register(INTCAPA)  # read interrupt register to clear it
    mcp23s17_read_register(INTCAPB)  # read interrupt register to clear it
    mcp23s17_write_register(IOCON, 0x28)  # Config register
    mcp23s17_write_register(IODIRA, 0xFF)  # Bank A are inputs
    mcp23s17_write_register(IODIRB, 0x00)  # Bank B all outputs
    mcp23s17_write_register(GPIOB, 0x00)  # All leds off
    mcp23s17_write_register(GPPUA, 0xFF)  # enable internal pull-up resistors on bank A
    mcp23s17_write_register(GPINTENA, 0xFF)  # Enable interrupts on bank A
    mcp23s17_write_register(DEFVALA, 0xFF)  # DEFVAL value for bank A
    mcp23s17_write_register(INTCONA, 0XFF)  # Trigger interrupt when pin state differs from DEFVALA
    LOG.debug('gpio: init function complete')


def init_epaper():
    """init spi device for epaper screen"""
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(BUSY_PIN, GPIO.IN)
    SPI_EPAPER.open(0, 1)
    SPI_EPAPER.max_speed_hz = 16000000
    SPI_EPAPER.mode = 0


def digital_write(pin: int, value: int):
    GPIO.output(pin, value)


def digital_read(pin: int):
    return GPIO.input(pin)


def delay_ms(delaytime: int) -> None:
    """delay in milliseconds"""
    sleep(delaytime / 1000.0)


def wait_for_arduino_int(timeout: int) -> None:
    return GPIO.wait_for_edge(config.ARDUINO_INT_PIN, GPIO.RISING, timeout=timeout)


def set_callback(pin: int, callback: Callable) -> None:
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=callback)


def epaper_transfer_data(data: Union[List[int], Tuple[int]]) -> None:
    """Spi transfer for array of bytes"""
    SPI_EPAPER.writebytes2(data)


def set_button_led(value: int) -> None:
    """
    Turn button leds on or off
    :param value: int, bit 1 is led on. 0 is off
    """
    mcp23s17_write_register(GPIOB, value)


def button_reset() -> None:
    """Reset the mcp23x17 ic"""
    digital_write(config.BUTTON_RESET_PIN, GPIO.LOW)
    delay_ms(1)
    digital_write(config.BUTTON_RESET_PIN, GPIO.HIGH)


def cleanup() -> None:
    """reset gpio pin configuration on the rpi"""
    GPIO.cleanup()


def epaper_read(reg: int, nr_of_bytes: int = 1):
    SPI_EPAPER.writebytes((reg,))
    return SPI_EPAPER.readbytes(nr_of_bytes)


def epaper_write(data: int, reg: int = None):
    """Spi transfer for single bytes"""
    if reg is not None:
        SPI_EPAPER.writebytes([reg, data])
    else:
        SPI_EPAPER.writebytes([data])


def mcp23s17_write_register(register: int, value: int) -> None:
    """
    param register: int: register
    param value: int: value
    """
    SPI_BUTTONS.xfer2([MCP_WRITE, register, value])


def mcp23s17_read_register(register: int) -> int:
    """
    param register: mcp23s17 register
    return list: values returned by spidev read method
    """
    incoming = SPI_BUTTONS.xfer2([MCP_READ, register, 0])
    return int(incoming[2])
