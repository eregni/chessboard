#!/usr/bin/env python3
"""
file actions on sdcard
"""

import logging
from typing import Optional
import jsonpickle
from chess import pgn

import config

LOG = logging.getLogger(__name__)


def save_game(path: str, content: pgn.Game) -> bool:
    """
    Save game to file
    :param path: string, path to file
    :param content: string: data to save
    :return: True/False --> successfull/Not successfull
    """
    try:
        print(content, file=open(path, 'w'), end='\n\n')

    except (OSError, IOError):
        LOG.exception('ERROR SAVING FILE')
        return False
        # TODO: WRITE SCREEN: 'THERE WAS A PROBLEM. FILE HAS NOT BEEN SAVED'
        # TODO ASK TO PUSH BUTTON TO CONTINUE

    return True


def save_move(path: str, content: str) -> None:
    """
    Save current computer move to file
    :param path: str: path to file
    :param content: str: contains chess move
    """
    try:
        print(content, file=open(path, 'w'), end='\n\n')

    except (OSError, IOError):
        LOG.exception('ERROR SAVING COMPUTER MOVE')


def save_setup(setup: config.Setup) -> None:
    """
    Save setup to file
    :param setup: string: data to save
    :return: True/False --> successfull/Not successfull
    """
    try:
        with open(config.SETUPFILE, 'w') as file:
            file.write(jsonpickle.encode(setup, indent=4))
    except (OSError, IOError):
        LOG.exception('ERROR SAVING SETUP FILE')


def open_saved_game(path: str) -> Optional[pgn.Game]:
    """
    Open savegame file.
    :param path: string, path to file
    :return: chess.pgn.Game or None
    """
    LOG.debug('looking for savegame file')
    try:
        with open(path, 'r') as file:
            load_pgn = pgn.read_game(file)
        return load_pgn
    except (IOError, FileNotFoundError):
        LOG.debug('No savegame file')
        return None


def open_setup(path: str) -> config.Setup:
    """
    Open setup file
    :param path: string, path to file
    :return: dict with file_uci_options from file or default file_uci_options
    """
    LOG.debug('Open setup file')
    try:
        with open(path) as file:
            data = jsonpickle.decode(file)
    except (FileNotFoundError, IOError):
        LOG.exception('No setup file found. Creating new with default setup')
        data = config.DEFAULT_SETUP
        with open(path, 'w') as file:
            file.write(jsonpickle.encode(config.DEFAULT_SETUP, indent=4))

    return data  # type: ignore


def open_move(path: str) -> str:
    """
    Open file containing the last calculated computer move
    :return: tuple containing 1 or 2 chess.Move (move + optional ponder)
    """
    move = ''
    LOG.debug('open previous computer move')
    try:
        with open(path, 'r') as file:
            move = file.readline()
    except (IOError, FileNotFoundError):
        LOG.debug('No previous computer move')

    return move
