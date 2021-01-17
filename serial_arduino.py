#!/usr/bin/env python3
"""Serial communication with the arduino """

import logging
import serial
import time
import lights
from enum import Enum

log = logging.getLogger(__name__)

START_CHAR = b'<'
STOP_CHAR = b'>'
SPLIT_CHAR = b'\t'
HELLO = b'H'
GIVE_BOARD = b'B'
GIVE_MOVE = b'M'
REED_ON = b'R'
REED_OFF = b'O'
ARDUINO_INT = b'I'
LED_MATRIX = b'L'
WHY_SHUTDOWN = b'S'

SER = serial.Serial(
    port="/dev/ttyAMA0",
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.5
)


# -------------------
# -- General stuff --
# -------------------
def _send_command(command: bytes) -> None:
    """
    Write to serial
    :param: command: bytes: command as a single char
    """
    cmd = b''.join([START_CHAR, command, STOP_CHAR])
    SER.write(cmd)


def _read_data() -> bytes:
    """Recieve from serial"""
    return SER.read_until(terminator=STOP_CHAR)


def _read() -> bytes:
    """Read 1 char"""
    return SER.read(1)


def _flush() -> None:
    """flush buffers"""
    SER.flushInput()
    SER.flushOutput()


def say_hello() -> bool:
    """
    mini 'pingtest'
    :returns True if succesfull
    """
    _send_command(HELLO)
    tried = 1
    while _read() != bytes(START_CHAR):
        if tried == 10:
            break

        time.sleep(0.1)
        log.error('Arduino, are you there?')
        tried += 1
        _send_command(HELLO)

    msg = _read_data()
    _flush()
    return True if msg == b'hello pi!' + STOP_CHAR else False


class ReasonInterrupt(Enum):
    """Interrupt codes coming from arduino"""
    NONE = 0
    MOVE = 1
    SHUTDOWN = 2
    BUTTONPRESS = 3


def get_interrupt_reason() -> int:
    """get the interrupt code"""
    incoming = _read_data().strip(START_CHAR + STOP_CHAR)
    return ReasonInterrupt(incoming)


# ------------------
# -- Board, moves --
# ------------------
def ask_board():
    """ask complete board. Returns list with 64 bits."""
    log.debug('Arduino, please give board')
    incoming = list()
    _send_command(GIVE_BOARD)
    while True:
        try:
            while _read() != START_CHAR:
                _send_command(GIVE_BOARD)
                time.sleep(0.01)

            # Get 8 bytes representing the board
            for index in range(8):
                incoming.append(ord(_read()))
                log.debug(incoming[index])

            check = _read()
            if check == STOP_CHAR:
                _flush()
                break
            else:
                log.error('Incoming board. Incorrect STOP_CHAR. Retry...' + str(check))

        except (UnicodeDecodeError, TypeError) as e:
            log.exception(str(e))
            log.exception('retry...')

        _flush()
    return make_square_set(incoming)


def make_square_set(incoming_data):
    """
    make square set
    :param incoming_data: list[string] incoming serial stream from arduino with complete board data
    :return: nr for chess.Squareset
    """
    # nr = 0
    # for row in range(8):
    #     value = incoming_data[row]
    #     for column in range(8):
    #         if value >> column & 1:
    #             nr += 1 << (row * 8 + column)
    #log = logging.getLogger(__name__)
    # log.debug('Incoming board: %s', nr)

    #  TODO Code has changed because the reed matrix was incorrectly soldered
    nr = 0
    for row in range(7, -1, -1):
        value = incoming_data[row]
        for column in range(8):
            if value >> column & 1:
                nr += 1 << ((7 - column) * 8 + 7 - row)

    log.debug('Incoming board: %s', nr)
    return nr


def new_detected_move():
    """Returns nr representing square where arduino detected movement.(0-63)"""
    log.debug('Asking move')
    while True:
        _send_command(GIVE_MOVE)
        try:
            while _read() != START_CHAR:
                time.sleep(0.01)  # Wait for arduino to send new move
                log.debug('Arduino, please give the new move')
                _send_command(GIVE_MOVE)

            new_move = ord(_read())

            # Check if incoming value is value from 0 to 63. 100 Indicates 'no move' (dummy button trigger)
            if new_move not in range(64) and new_move != 100:
                log.warning('ERROR: incoming move not possible retry...' + str(new_move))
            else:
                _flush()
                break

        except (UnicodeDecodeError, TypeError) as e:
            log.exception(e + " Retry...")

        _flush()

    return new_move


def reed_on():
    _send_command(REED_ON)
    log.debug('Reed on')
    while _read() != START_CHAR:
        _send_command(REED_ON)
        time.sleep(0.01)

    confirm = _read_data()
    if confirm != b'on>':
        log.critical('Reed on: NOT confirmed! --> %s', confirm)

    _flush()


def reed_off():
    _send_command(REED_OFF)
    log.debug('Reed off')
    while _read() != START_CHAR:
        _send_command(REED_OFF)
        time.sleep(0.01)

    confirm = _read_data()
    if confirm != b'off>':
        log.critical('Reed off: NOT confirmed! --> %s', confirm)

    _flush()


def trigger_arduino_int():
    log.debug('reed triggered')
    _send_command(ARDUINO_INT)


# -----------------
# -- board leds ---
# -----------------
def update_leds(action, *args):
    """
    Send action to square.
    :param action: Action from lights.LedCommands
    :param args:
    :return:
    """
    if action not in lights.LedCommands:
        log.fatal("Update leds: Incorrect action")
        raise ValueError

    SER.write(LED_MATRIX)
    SER.write(action)
    for item in args:
        if isinstance(item, list):
            for square in item:
                SER.write(square)

            SER.write(SPLIT_CHAR)

        else:
            SER.write(item)

    SER.write(SPLIT_CHAR)
