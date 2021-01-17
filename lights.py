#!/usr/bin/env python3

# FUNCTIONS
# blink square
# animante move
# move done
# wait for move confirmation
# promotion
# en passant
# indicate missing pieces
# clear square
# clear leds

import logging
import serial_arduino
from enum import Enum

log = logging.getLogger(__name__)

_ledstates = [False] * 64


class LedCommands(Enum):
    SQUARE_ON = 1
    SQUARE_OFF = 2
    CLEAR_LEDS = 3


def blink_square(square, color):
    """
    Used for indicate picked up piece, alert wrong move
    :param square: square nr (0 - 63)
    :param color: list with RGB values
    :return:
    """
    serial_arduino.update_leds(LedCommands.SQUARE_ON, 1, square, color[0], color[1], color[2])
    _ledstates[square] = True


def animate_move(from_square, to_square, from_color, to_color):
    """
    Used for hints, last move, current player/computer move
    :param from_square: 0 - 63
    :param to_square: 0 - 63
    :param from_color: list with RGB values first square
    :param to_color: list with RGB values second square
    :return:
    """
    clear_leds()
    _square_on(1, from_square, from_color[0], from_color[1], from_color[2])
    _square_on(2, to_square, to_color[0], to_color[1], to_color[2])
    _ledstates[from_square] = True
    _ledstates[to_square] = True


def move_done():
    raise NotImplementedError


def wait_for_confirmation(from_square, to_square):
    """
    Animation when program is waiting for player to confirm move
    :param from_square: 0-63
    :param to_square: 0-63
    :return:
    """
    clear_leds()
    _square_on(1, [from_square, to_square], 0, 255, 0)


def promotion():
    raise NotImplementedError


def en_passant():
    raise NotImplementedError


def indicate_missing_pieces(missing, wrong):
    """
    :param missing: list with missing squares
    :param wrong: list with incorrect squares
    :return:
    """
    clear_leds()
    for square in missing:
        serial_arduino.update_leds(LedCommands.SQUARE_ON, square, 1, 255, 100, 0)
        _ledstates[square] = True

    for square in wrong:
        serial_arduino.update_leds((LedCommands.SQUARE_ON, square, 1, 255, 0, 0))
        _ledstates[square] = True


def clear_square():
    raise NotImplementedError


def clear_leds():
    """
    All leds off
    :return:
    """
    serial_arduino.update_leds(LedCommands.CLEAR_LEDS)
    for square in range(64):
        _ledstates[square] = False


# ########################################################
def _square_on(frame, squares, red, green, blue):
    """
    Turn on 1 - 64 squares on led matrix
    :param frame: frame nr (1 - 8)
    :param squares: int OR list, nr 1 - 64
    :param red: brightness red (0 - 255)
    :param green:  brightness red (0 - 255)
    :param blue:  brightness red (0 - 255)
    :return: 
    """
    if frame not in range(8) or squares not in range(65) or (red, green, blue) not in range(256):
        _incorrect_value('_square_on', frame, squares, red, green, blue)

    serial_arduino.update_leds(LedCommands.SQUARE_ON, squares, red, blue, green)


def _square_off(frame, squares):
    """
    Turn off 1 - 64 squares on led matrix
    :param frame: frame nr (0 - 7)
    :param squares: squares: int OR list, nr 1 - 64
    :return:
    """
    if frame not in range(8) or squares not in range(65):
        _incorrect_value('_square_off', frame, squares)
    serial_arduino.update_leds(LedCommands.SQUARE_OFF, frame, squares)


def _incorrect_value(func, *args):
    """
    Raise ValueError
    :param function: string, function name
    :param args: value(s)
    :return:
    """
    log.error('lights: incorrect value: {1}'.format(func, [' {} '.format(item) for item in args]))
    raise ValueError('{0}: Incorrect value: {1}'.format(func, [' {} '.format(item) for item in args]))
