#!/usr/bin/env python3
"""Constant and configuration objects"""
import configparser
import csv
import logging
from PIL import ImageFont
from typing import Union, Dict, NamedTuple, List, Any
from typing import NewType
from dataclasses import dataclass

LOG = logging.getLogger(__name__)

WHITE = True
BLACK = False
ON = True
OFF = False
EMPTY_BOARD = '!""""""""#\n$ + + + +%\n$+ + + + %\n$ + + + +%\n$+ + + + %\n' \
              '$ + + + +%\n$+ + + + %\n$ + + + +%\n$+ + + + %\n/(((((((()'

# ------------
# -- Epaper --
# ------------
LANDSCAPE = False
PORTRAIT = True
ORIENTATION = NewType('ORIENTATION', bool)
LEFT = 0
RIGHT = 1
CENTER = 2
IMG_BUTTON_RIGHT = 'images/button_right.png'
IMG_BUTTON_LEFT = 'images/button_left.png'
ASCII_PIECES = (167, 164, 165, 166, 163, 162)

# -----------
# -- files --
# -----------
SAVEGAME = 'savegame.pgn'
SETUPFILE = 'setup.json'
COMPUTER_MOVE = 'computer.move'
LOG_FILE = 'log/program.log'

# --------------------
# -- Epaper/epd4in2 --
# --------------------
DEVICE_WIDTH = 400
DEVICE_HEIGHT = 300
FULL_REFRESH = 10
FONT_PATH = 'font/FreeMonoBold.ttf'
FONT_SMALL_MAX = ImageFont.truetype(FONT_PATH, 12)
FONT_SMALL = ImageFont.truetype(FONT_PATH, 14)
FONT_NORMAL = ImageFont.truetype(FONT_PATH, 18)
FONT_BIG = ImageFont.truetype(FONT_PATH, 22)
FONT_BIGGER = ImageFont.truetype(FONT_PATH, 36)
FONT_VERY_BIG = ImageFont.truetype(FONT_PATH, 80)
CHESS_FONT_PATH = 'font/CASEFONT.ttf'
CHESS_FONT = ImageFont.truetype(CHESS_FONT_PATH, 28)
CHESS_FONT_VERY_BIG = ImageFont.truetype(CHESS_FONT_PATH, 80)
CHAR_WIDTH = 11
RODENT_IMAGES = 'images/rodent_personalities/'
MAIN_PERSONALITY_IMAGE = 'images/calvin/calvin_running.png'

# ----------
# -- Gpio --
# ----------
# Arduino interrupt
ARDUINO_INT_PIN = 25
# epaper
RST_PIN = 20
DC_PIN = 26
CS_EPAPER_PIN = 7
BUSY_PIN = 21
# button panel
CS_BUTTON_PIN = 8
BUTTON_RESET_PIN = 4
BUTTON_DEBOUNCE = 100  # Millisec
AUTOSHUTDOWN = 3600  # Sec
TIME_CONFIRM_MOVE = 3  # 1 sec more than you see on the commander because it updates a bit slow :-)
# led
GREEN_ACTIVITY_LED = 47  # GPIO 47 is the led on rpi zero
DEFAULT_BRIGHTNESS = 511  # (0-4095)


# -------------
# -- Options --
# -------------
@dataclass
class Option:
    """Object containing variables for a game option"""
    name: str
    value: Any
    unit: Union[str, None] = None
    options: Union[tuple, list, range, None] = None

    def __str__(self) -> str:
        return '{0}: name={1}'.format(type(self), self.name)

    def __repr__(self) -> str:
        return '{0} value={1} unit={2}'.format(self.__str__(), self.value, self.unit)


# options with their default value
COLOR = Option(name='Color', value=WHITE)
MOVETIME = Option(name='Movetime', value=5, unit=' sec', options=(5, 15, 30, 60, 300, 600, 900, 0))
MARKERS = Option(name='Markers', value=True)
MARK_LAST_MOVE = Option(name='Mark last move', value=False)
WAIT_TO_CONFIRM = Option(name='Wait to confirm', value=True)
ENGINES: list = []


# -------------------
# -- Chess engines --
# -------------------
class EngineSetup:
    """
    Object containing all variables for the chess engine
    The ponder setting is always disabled since the board is running on batteries
        name: Name visible on screen
        version: visible version
        path: path of engine executable
        licence: licence type
        description: text, short engine descrition for the screen.
        logo: path to logo image. MAX height=100px, MAX width=175
        protocol: uci or xboard
        exec_args: CLI options for the engine
        options: dict containing options which the user can adjust
        **kwargs: dict containing engine specific options (openening books, endgame tables, hash size...). The key is
        used in the uci 'setoption' command
    """

    def __init__(self, name: str, version: str, path: Union[str, List[str]], licence: str, description: str, logo: str, protocol: str,
                 exec_args: str = None, options: dict = None, **kwargs) -> None:
        self.options: Dict[str, Option] = {'movetime': MOVETIME}
        self.name = name
        self.version = version
        self.path = path
        self.licence = licence
        self.description = description
        self.logo = logo
        self.protocol = protocol
        self.exec_args = exec_args
        self.options['level'] = Option('level', 'no levels')
        if options:
            self.options.update(options)
        self.ponder = False
        self.extra_options: Dict[str, Union[str, int]] = {}  # for extra, engine specific, options not for user (eg. 'hash', 'book', ...)
        for item, value in kwargs.items():
            self.extra_options[item] = value

        # global ENGINES
        ENGINES.append(self)

    def __eq__(self, other) -> bool:
        return self.name == other.name

    def __str__(self) -> str:
        return '{0}: {1}'.format(type(self), self.name)

    def __repr__(self) -> str:
        return '{0}: {1}'.format(type(self), self.name)


# --------------------------
# -- Chess engine configs --
# --------------------------
STOCKFISH = EngineSetup(
    name='Stockfish',
    version='11',
    path='engines/stockfish/stockfish',
    licence='GPLv3',
    description='Engine written by Tord Romstad, Marco Costalba, Joona Kiiski, and Gary Linscott. Stockfish is '
                'universally recognized as the strongest open source engine in the world. The name "Stockfish" '
                'reflects the ancestry of the engine. Tord is Norwegian and Marco Italian, and there is a long history'
                ' of stockfish trade from Norway to Italy.',
    logo='images/logo/stockfish.png',
    protocol='uci',
    options={'level': Option(name='Skill Level', value=20, unit='/20', options=[*range(21)])},
    ponder=False,
    Hash=256,
    SyzygyProbePath='syzigy/',  # http://oics.olympuschess.com/tracker/index.php,
)

GREKO = EngineSetup(  # TODO complete -> need extra command "uci" after start
    name='Greko',
    version='2020.03',
    path='engines/greko/GreKo',
    licence='?',
    description='An open source engine by Vladimir Medvedev, written in C++, started in 2002.',
    logo='images/logo/greko.png',
    protocol='uci',
    ponder=False,
)

SAYURI = EngineSetup(
    name='Sayuri',
    version='20180523',
    path='engines/sayuri/sayuri',
    licence='MIT',
    description='An open source chess engine written by Hironori Ishibashi in C++11, first published in 2013. Sayuri has an embedded '
                'LISP interpreter dubbed Sayulisp, which can generate and operate the chess engine, and customize search algorithms '
                'and evaluation weights.',
    logo='images/logo/sayuri.png',
    protocol='uci',
    ponder=False,
)

GALJOEN = EngineSetup(
    name='Galjoen',
    version='0.40.1',
    path='engines/galjoen/galjoen_eng',
    licence='GPL',
    description='An open source chess program by Werner Taelemans, written in C++11, first released in February 2015.',
    logo='images/logo/galjoen.png',
    protocol='uci',
    ponder=False,
)

CINNAMON = EngineSetup(
    name='Cinnamon',
    version='2.2a',
    path='engines/',
    licence='GPLv3',
    description='Cinnamon is an open source chess engine by Giuseppe Cannella, written in C++11. Cinnamon was first released in '
                'February 2013 under that name, while former versions of the engine were called Butterfly.',
    logo='images/logo/cinnamon.png',
    protocol='uci',
    ponder=False,
)

GUNCHESS = EngineSetup(  # TODO investigate --> segmentation errors when sending uci 'quit' command
    name='GNU-chess',
    version='6.2.7',
    path=['engines/gnuchess/gnuchess', '-u'],
    licence='GPLv3',
    description='The open source chess engine of the Free Software Foundation. GNU Chess was initially written by Stuart Cracraft '
                'in the mid 80s. Dozens of developers have enhanced GNU Chess over the times. Fabien Letouzey is the primary author '
                'of GNU Chess 6, based on Fruit 2.1',
    logo='images/logo/gnuchess.png',
    protocol='uci',
    ponder=False,
)

LASER = EngineSetup(
    name='Laser',
    version='1.8 beta',
    path='engines/laser/laser',
    licence='GPLv3',
    description='An open source chess engine by Jeffrey An and Michael An, written in C++11, first released in summer 2015.',
    logo='images/logo/laser.png',
    protocol='uci',
    ponder=False,
)


# RODENT...
class Person(NamedTuple):
    """Object containing settings for different Rodent personalities"""
    name: str
    category: str
    country: str
    description: str
    active: str
    life: str = None
    image: str = None


def rodent_get_uci_options(person: Person) -> dict:
    """
    Get uci options for given Person
    :param person: Person
    :return: dict with uci options
    """
    return dict(RODENT_UCI[person.name].items())


# Personalities
# read uci options for each personality from file
RODENT_UCI = configparser.ConfigParser(allow_no_value=True)
with open('engines/rodent/rodent.uci', 'r') as ini_file:
    RODENT_UCI.read_file(ini_file)

with open('engines/rodent/personalities_info.csv', 'r') as csv_file:
    RODENT_PERSONALIIES = []
    table = csv.reader(csv_file)
    for row in csv.reader(csv_file):
        RODENT_PERSONALIIES.append(Person(row[0], row[1], row[2], row[3], row[4], row[5], row[6]))

RODENT = EngineSetup(
    name='Rodent',
    version='III',
    options={'level': Option(name='level', value=RODENT_PERSONALIIES[0], options=RODENT_PERSONALIIES)},
    path='engines/rodent/rodentIII',
    logo='images/logo/rodent.png',
    protocol='uci',
    ponder=False,
    licence='GPLv3',
    description='Rodent III is a chess engine written by Pawel Koziol. Instead of levels it can adopt personalities: '
                'it offers different playing styles rather than strength levels. RodentIII can be turned into a strong'
                ' GM as into a beginning kid. It has both serious and funny personalities. There are also setups who immitate '
                'famous players styles',
    Hash=256)


# -----------
# -- Setup --
# -----------
@dataclass
class Setup:
    """Object containing game settings"""
    color: Option
    engine: EngineSetup
    markers: Option
    mark_last_move: Option
    wait_to_confirm: Option


# Default Setup
DEFAULT_SETUP = Setup(
    COLOR,
    ENGINES[0],
    MARKERS,
    MARK_LAST_MOVE,
    WAIT_TO_CONFIRM
)
