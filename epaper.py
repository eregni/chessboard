#!/usr/bin/env python
"""
Epaper:
    - Compose frame objes
    - Send commands to commander (ex. update_frame())

frames:
boot_screen             OK
clear_screen            OK
main_color		        OK
main_engine             OK
main_engine_options     OK
main_markers            OK
main_mark_last_move     OK
main_time_confirm_move  OK
main_defaults           OK

game_new                OK
game_player_turn	    OK
game_computer_turn	    OK
game_give_hint			OK
game_show_attackers		OK  NOT USED
game_end_game		    OK
game_validate_board		OK
show_board              OK
game_led_options        OK
"""

import logging
from time import sleep, perf_counter
from functools import partial
import threading
import queue
import textwrap
from typing import List, Tuple, Union, TypeVar, Callable, Generic
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import chess

import config
import button
from button import Button
import epd4in2
import frame_array

LOG = logging.getLogger(__name__)


#######################
# ## BUILDING BLOCKS ##
#######################
@dataclass
class FrameRectangle:
    """Make a rectangle"""
    measurements: Tuple[int, int, int, int]
    fill: bool = config.BLACK


@dataclass
class FrameImage:
    """Make frameItem from an image"""
    path: str
    pos: Tuple[int, int] = (0, 0)


@dataclass
class FrameText:
    """Make frameItem from str/text"""
    content: str
    pos: Tuple[int, int] = (0, 0)
    align: int = config.LEFT
    fill: bool = config.BLACK
    font: config.ImageFont.truetype = config.FONT_NORMAL
    spacing: int = 6

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return self.content


@dataclass
class FrameBoard(FrameText):
    """Chessboard in string format to display on the epaper"""
    content = config.EMPTY_BOARD


FrameItems = TypeVar('FrameItems', FrameRectangle, FrameImage, FrameText)


@dataclass
class Frame(Generic[FrameItems]):
    """
    Object containing items to be sent to the epaper. It is possible to make name and id_name different which is
    usefull for frame with a variable name (e.g. frame 'question')
    """
    name: str
    orientation: bool = config.LANDSCAPE
    important: bool = True
    buttons: Union[List[Button], Tuple[Button]] = None
    items: List[FrameItems] = None

    def __str__(self) -> str:
        return '{0} name={1}'.format(self.__class__, self.name)

    def __repr__(self) -> str:
        return self.__str__()


class PartialFrame(Frame):
    """
    Same object as Frame but doesn't cover the whole screen.
    PartialFrame is used to make the commander refresh faster.
    Has no buttons
    """
    def __init__(self, name, important=False, items=None, width=0, height=0, pos=(0, 0)):
        super().__init__(name=name, important=important, items=items)
        self.width: int = width
        self.height: int = height
        self.pos: Tuple[int, int] = pos


class FrameArray(Frame):
    """
    frame containing a pre-calculated array from the frame_array module. This way, A screen refresh job can skip a few
    steps and save time.
    This is the fastest method to refresh the epapar but it can only be used for static frames (no variable parts).
    """
    def __init__(self, name, content, buttons, important=False):
        super().__init__(name=name, buttons=buttons, important=important)
        self.content: Tuple[int] = content


FrameTypes = TypeVar('FrameTypes', Frame, PartialFrame, FrameArray)

# ------------------------
# -- Static frame items --
# ------------------------
FOOTER = FrameRectangle(measurements=(0, 275, 400, 300))
FOOTER_LARGE = FrameRectangle(measurements=(0, 208, 400, 300))
TITLE_DECORATION_LEFT = FrameText(content='nqp', pos=(3, 3), font=config.CHESS_FONT, fill=config.WHITE)
TITLE_DECORATION_RIGHT = FrameText(content='rnk', pos=(315, 3), font=config.CHESS_FONT, fill=config.WHITE)
PLAYER_WAIT = FrameText(content='Waiting for move...', pos=(15, 6), fill=config.WHITE)
PLAYER_MOVE_CONFIRMED = FrameText(content='Confirmed', pos=(15, 25), fill=config.WHITE, font=config.FONT_BIGGER, align=config.CENTER)

# --------------------------
# -- Static PartialFrames --
# --------------------------
PLAYER_CONFIRM = PartialFrame(name='player_confirm', width=180, height=48, pos=(224, 166), items=[FrameRectangle(measurements=(0, 0, 180, 48)), FrameText(pos=(6, 3), fill=config.WHITE, content=textwrap.fill('Wait {0} seconds to confirm move'.format(config.TIME_CONFIRM_MOVE - 1), width=16))])
COMPUTER_CONFIRM = PartialFrame(name='conputer_confirm', width=176, height=48, pos=(0, 164), items=[FrameRectangle(measurements=(0, 0, 176, 48)), FrameText(content=textwrap.fill('Waiting for confirmed move', width=16), fill=config.WHITE, pos=(15, 3))])
PLAYER_HINT = PartialFrame(name='hint', width=200, height=40, pos=(200, 165), items=[FrameText(content='Hint:', font=config.FONT_BIGGER, pos=(25, 3), fill=config.BLACK)])
PGN_SAVED = PartialFrame('pgn_saved', items=[FOOTER_LARGE, FrameText(content='Confirmed', pos=(15, 25), fill=config.WHITE, font=config.FONT_BIGGER, align=config.CENTER)], pos=(0, 208), height=208, width=400)


class Screen:
    """Manage screen-refresh jobs"""
    def __init__(self, menu_items: List[Callable]):
        """:param menu_items: list containing functions who return a Frame"""
        self.enabled = True
        self.threadlock_screen = threading.Lock()
        self.screen_queue = queue.Queue()
        self.ignore_unimportant = threading.Event()
        self.epd = epd4in2.EPDisplay()
        self.main_menu = menu_items
        self._get_menu_item = iter(self.main_menu)
        LOG.debug('epaper init done')

    def busy(self) -> bool:
        """Return True if the Screen thread is running"""
        return self.threadlock_screen.locked()

    def update_engine_options(self, engine: config.EngineSetup) -> None:
        """
        Update the engine frame methods in the main_menu
        :param engine: Setup.engine.options
        :return:
        """
        for frame in self.main_menu:
            if isinstance(frame, partial):
                self.main_menu.remove(frame)

        for option in engine.options:
            self.main_menu.insert(3, partial(main_engine_options, option=option))

    def get_menu_item(self, first: bool = False) -> Callable:
        """
        Get next item from main_menu
        :return: function to make a frames.Frame
        """
        while True:
            if first:
                self._get_menu_item = iter(self.main_menu)
            try:
                return next(self._get_menu_item)
            except StopIteration:
                self._get_menu_item = iter(self.main_menu)
                continue

    def update_frame(self, button_panel: button.Panel, frame: Union[FrameTypes, Tuple[FrameTypes]], important: bool = True) -> None:
        """
        Update frame on epaper display
        :param button_panel, button.Panel object
        :param frame: FrameTypes, tuple with FrameTypes
        :param important: bool: Setup True will make sure the screen will not be discarted when there are too many
            frames waiting in the queue, or in case the queue gets cleared
        :return:
        """
        def update(frm: FrameTypes, timestamp: float) -> None:
            if important:
                LOG.debug('Important frame!')
                self._clear_queue()
            self._new_refresh_task(button_panel, frm, important, timestamp)

        stamp = 0.0
        if LOG.getEffectiveLevel() == logging.DEBUG:
            stamp = perf_counter()

        if not self.enabled:
            LOG.debug('Frame %s dropped because screen is disabled', frame.name)
            return
        LOG.debug('Update screen: %s', type(frame))

        if isinstance(frame, tuple):
            for item in frame:
                update(item, stamp)
        else:
            update(frame, stamp)

    def clear_screen(self, button_panel: button.Panel, message: str = None, full_refresh: bool = True) -> None:
        """
        Send blank screen to epaper with optional message in the center
        :param button_panel: button.Panel
        :param message: str: Message to show in the center of the blank screen
        :param full_refresh: bool: set True to force a full refresh to prevent ghosting of previous frames
        """
        if message is not None:
            text = FrameText(content=message, pos=(0, 140), align=config.CENTER)
            frame = Frame(name='', items=[text, FOOTER])
            content = _get_frame_buffer(_draw_screen(frame))
        else:
            content = tuple([0xFF] * (config.DEVICE_WIDTH * config.DEVICE_HEIGHT // 8))

        image = FrameArray("clear with message", content=content, buttons=None, important=True)
        self._new_refresh_task(button_panel, image, important=True, stamp=float(0), full_refresh=full_refresh)
        LOG.debug("Screen cleared")

    def sleep(self):
        """Set the epaper in sleep mode"""
        self.epd.sleep()

    def _new_refresh_task(self, button_panel: button.Panel, frame: FrameTypes, important: bool, stamp: float,
                          full_refresh: bool = False) -> None:
        """
        Creates screen_update task and adds it to the queue
        Starts the epaper-thread if it is not running
        :param button_panel: button.Panel object
        :param frame: FrameTypes
        :param important: bool, if set True the Screen will drop refresh jobs from screen_queue. This way the program will skip frames
            when the user makes many button presses short time. I won't be nice to wait for ALL the refresh jobs to pass
        :param stamp: Time.perf_counter DEBUG
        :param full_refresh: True to force a full refresh
        :return:
        """
        LOG.debug('Screen: New refresh task: frame: %s, frame type=%s, important=%s', frame.name, type(frame), important)
        partial_frame_setup = None if not isinstance(frame, PartialFrame) else (frame.pos, frame.height, frame.width)
        job = (frame, important, partial_frame_setup, stamp, full_refresh)
        self.screen_queue.put(job)

        if not self.threadlock_screen.locked():
            refresh = EpaperThread(self, button_panel)
            refresh.start()

    def _clear_queue(self) -> None:
        """Hold program until all frames are send to epaper. Ignore 'unimportant frames just to speed things up."""
        if not self.screen_queue.empty():
            LOG.debug('Waiting until screen queue is empty...')
            self.ignore_unimportant.set()
            while self.threadlock_screen.locked():
                sleep(0.02)
            self.ignore_unimportant.clear()

        else:
            LOG.debug('commander.clear_que: no screen thread running')


def prefetch(frame: FrameTypes) -> tuple:
    """
    Get tuple containing c-string from image.
    The function is only used by the frame_buffers.py script
    """
    image = _draw_screen(frame)
    return _get_frame_buffer(image)


def _init_image(frame: FrameTypes) -> Image:
    """Set width and height according to screen orientation and generate empty Image and draw"""
    if isinstance(frame, PartialFrame):
        image = Image.new('1', (frame.width, frame.height), 255)  # Blank partial frame
    else:
        image = Image.new('1', (config.DEVICE_WIDTH, config.DEVICE_HEIGHT), 255)  # Blank frame

    return image


def _add_text_middle(draw: ImageDraw.Draw, y_pos: int, text: FrameText, font: ImageFont, fill: bool, width=-1, offset_x=0) -> None:
    """Add text to middle of block
    :param y_pos: y in screen
    :param text: text to add
    :param font: font to use
    :param fill: fill of text
    :param width: width of block
    :param offset_x: offset in x of the block
    :return:
    """

    if width == -1:
        width = epd4in2.EPD_WIDTH

    _, h_origin = font.getsize("a")
    w, h = font.getsize(text.content)

    # Vertical offset for symbol fonts
    offset_y = 0
    if h - h_origin > 5:
        offset_y = h - h_origin

    draw.text((offset_x + width / 2 - w / 2, y_pos - offset_y), text.content, font=font, fill=fill)


def _draw_screen(frame: FrameTypes) -> Image:
    """Create image to send to epaper"""
    image = _init_image(frame)
    draw = ImageDraw.Draw(image)

    # Draw frame title
    if not isinstance(frame, PartialFrame):
        draw.rectangle((0, 0, config.DEVICE_WIDTH, 30), fill=config.BLACK)
        text = FrameText(frame.name)
        _add_text_middle(draw, 8, text, font=config.FONT_NORMAL, fill=config.WHITE)

    if frame.items:
        for item in frame.items:
            _draw_frame_item(image, draw, item)

    if frame.buttons:
        x_default = 15
        y_pos = 43
        right_y_pos = 43
        for btn in frame.buttons:
            if btn.align == config.RIGHT:
                btn_text = '{1}({0}'.format(btn.call_nr, btn.name)
                x_pos = epd4in2.EPD_WIDTH - x_default - (len(btn_text) * config.CHAR_WIDTH)
                with Image.open(config.IMG_BUTTON_LEFT) as image_button_left:
                    image.paste(image_button_left, (x_pos - image_button_left.width, right_y_pos - 1))
                draw.rectangle((x_pos, right_y_pos - 1, x_pos + config.CHAR_WIDTH * len(btn_text), right_y_pos + 20), fill=config.BLACK)
                with Image.open(config.IMG_BUTTON_RIGHT) as image_button_right:
                    image.paste(image_button_right, (x_pos + len(btn_text) * config.CHAR_WIDTH + 1, right_y_pos - 1))
                draw.text((x_pos, right_y_pos), btn_text, font=config.FONT_NORMAL, fill=config.WHITE)
                right_y_pos += 40
            else:
                btn_text = '{0}) {1}'.format(btn.call_nr, btn.name)
                with Image.open(config.IMG_BUTTON_LEFT) as image_button_left:
                    image.paste(image_button_left, (x_default - image_button_left.width, y_pos - 1))
                draw.rectangle((x_default, y_pos - 1, x_default + config.CHAR_WIDTH * len(btn_text), y_pos + 20), fill=config.BLACK)
                with Image.open(config.IMG_BUTTON_RIGHT) as image_button_right:
                    image.paste(image_button_right, (x_default + len(btn_text) * config.CHAR_WIDTH + 1, y_pos - 1))
                draw.text((x_default, y_pos), btn_text, font=config.FONT_NORMAL, fill=config.WHITE)
                y_pos += 40

    return image


def _draw_frame_item(image: Image, draw: ImageDraw.Draw, item: FrameItems) -> None:
    """Add FrameItems to the image"""
    if isinstance(item, FrameImage):
        with Image.open(item.path) as im:
            image.paste(im, item.pos)

    elif isinstance(item, FrameBoard):
        board = Image.new('1', (300, 300), 255)
        board_draw = ImageDraw.Draw(board)
        board_draw.multiline_text(item.pos, item.content, font=item.font, spacing=item.spacing, fill=item.fill)
        board = board.rotate(-90)
        image.paste(board, (-6, 46))

    elif isinstance(item, FrameRectangle):
        draw.rectangle(item.measurements, fill=item.fill)

    elif isinstance(item, FrameText):
        if item.align == config.CENTER:
            _add_text_middle(draw, item.pos[1], item, font=item.font, fill=item.fill, width=image.width)
        else:
            draw.multiline_text(item.pos, item.content, font=item.font, spacing=item.spacing, fill=item.fill)
    else:
        raise TypeError('ERROR: Unknown FrameItem type passed %s', type(item))


def _get_frame_buffer(image: Image) -> Tuple[bytes]:
    """
    Create framebuffer from given image
    :return: tuple
    """
    image_monocolor = image.convert('1')
    return tuple(image_monocolor.tobytes())  # type: ignore


class EpaperThread(threading.Thread):
    """Send frames to epaper in seperate thread"""
    def __init__(self, screen, button_panel):
        super().__init__(name='ScreenThread')
        self.screen: Screen = screen
        self.button_panel: button.Panel = button_panel

    def run(self) -> None:
        self.screen.threadlock_screen.acquire()
        LOG.debug('Screen thread spawned')
        while not self.screen.screen_queue.empty():
            frame, important, partial_frame_setup, stamp, full_refresh = self.screen.screen_queue.get(timeout=5)

            if not self.screen.ignore_unimportant.is_set() or important:
                if frame.buttons:
                    self.button_panel.update_buttons(frame.buttons)
                    button.Panel.toggle_alarm()

                image_live = frame.content if isinstance(frame, FrameArray) else _get_frame_buffer(_draw_screen(frame))
                self.screen.epd.send_to_epaper(image_live, stamp, partial_frame_setup, full_refresh)

            else:
                LOG.debug("Ignored frame because self.screen.ignore_unimportant.is_set() == True")

        LOG.debug('Screen thread finished')
        self.screen.threadlock_screen.release()


# ------------
# -- Frames --
# ------------
def main_info(button_panel: button.Panel, setup: config.Setup = None, partial_frame: bool = False) -> FrameTypes:
    """
    First item in the Main Menu
    :param button_panel, dict with button.Button object
    :param setup = MAIN.GAME. Only neccesary in case of a PartialFrame
    :param partial_frame: bool: True if the frame is a partial frame
    :return: Tuple[FrameArray, PartialFrame]
    """
    if not partial_frame:
        buttons = [button_panel.buttons.start_new_game, button_panel.buttons.options]
        frame = FrameArray('main_info', content=frame_array.menu, buttons=buttons)

    else:
        engine = setup.engine
        items = ['{0}: {1}{2}\n'.format(option.name, option.value, option.unit) for key, option in engine.options.items() if key != 'level']
        if 'level' in engine.options.keys():
            level = engine.options['level'].value
            if isinstance(level, config.Person):
                items.append('Personality: {0}\n'.format(level.name))
            else:
                items.append('Level: {0}\n'.format(level))

        if len(items) > 2:
            raise NotImplementedError(LOG.critical('Screen:main_info: There is only place for 2 engine options on the e-paper so far'))
        text0 = ''.join(items)
        color = 'white' if setup.color.value else 'black'
        text1 = FrameText(content=''.join(['{0} {1}\n'.format(engine.name, engine.version), text0, 'Player is ', color]), pos=(15, 6), fill=config.WHITE, spacing=6)
        rectangle = FrameRectangle(measurements=(0, 0, 400, 110))
        frame = PartialFrame(name='main_info', items=[rectangle, text1], width=400, height=110, pos=(0, 208))

    return frame


def main_color(button_panel: button.Panel, setup: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    If no setup are given the function will return the FrameArray
    :param button_panel, dict with button.Button object
    :param setup: GAME.file. Necessary in case of a partial engine
    :param partial_frame: Set True is frame needs to be the partail frame
    :return: FrameTypes
    """
    if not partial_frame:
        buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, Button('Toggle', partial(button_panel.callbacks['toggle_option'], option=setup.color), call_nr=3))
        frame = FrameArray(name='main_color', content=frame_array.choose_color, buttons=buttons)
    else:
        setup = setup.color.value
        text0 = FrameText(content=''.join(('Selected color:\n',)), pos=(15, 6), fill=config.WHITE)
        text1 = FrameText(content='White' if setup is config.WHITE else 'Black', pos=(15, 28), fill=config.WHITE, font=config.FONT_BIGGER, align=config.CENTER)
        rectangle = FrameRectangle(measurements=(0, 0, 184, 92))

        frame = PartialFrame(name='color', items=[rectangle, text0, text1], width=184, height=92, pos=(0, 208))

    return frame


def main_engine(button_panel: button.Panel, setup: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    :param button_panel, dict with button.Button object
    :param setup: config.Setup
    :param partial_frame. Set True to get the partial frame
    :return: Tuple[FrameTypes]
    """
    if not partial_frame:
        buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, button_panel.buttons.next_engine)
        frame = FrameArray(name='main_engine', content=frame_array.engine, buttons=buttons)

    else:
        engine = setup.engine
        # content = '{0} {1}'.format(engine.name, engine.version)
        # text0 = FrameText(content=content, pos=(15, 2), fill=config.WHITE, font=config.FONT_NORMAL, align=config.CENTER)
        text = FrameText(content=textwrap.fill(engine.description, width=48), pos=(10, 2), fill=config.WHITE, font=config.FONT_SMALL, spacing=3)
        rectangle = FrameRectangle(measurements=(0, 0, 400, 150))
        frame = engine_logo(setup), PartialFrame(name='engine', items=[rectangle, text], width=400, height=150, pos=(0, 168))

    return frame


def engine_logo(setup: config.Setup) -> PartialFrame:
    """
    The logo image should have a max heigth: 100 and max width 174. The image should also text with engine info
    :param setup: GAME.setup
    :return: PartialFrame containing an image of the engine's logo
    """
    with Image.open(setup.engine.logo) as im:
        im_pos = 87 - im.width // 2  # image max width / 2
    logo = FrameImage(path=setup.engine.logo, pos=(im_pos, 5))
    text = FrameText('{0} {1}'.format(setup.engine.name, setup.engine.version), pos=(1, 105), align=config.CENTER)
    return PartialFrame(name='engine logo', width=176, height=129, items=[logo, text], pos=(220, 31))


def main_engine_options(button_panel: button.Panel, option: Union[config.Option, config.Person], partial_frame: bool) -> Union[Frame, PartialFrame]:
    """
    frame for specific engine options.
    PartialFrame contains info for specific option.
    :param button_panel, dict with button.Button object
    :param option: config.Opt# import RPi.GPIO as GPIO
    :param partial_frame: bool. Get full or partial frame. Partial frame returns variable option info
    :param partial_frame. Set True to get the partial frame
    :return: rpi_zero.Frame or rpi_zero.PartialFrame
    """
    if isinstance(option.value, config.Person):
        frame = main_personality_option(button_panel, option.value)

    elif isinstance(option, config.Option):
        if not partial_frame:
            buttons = [button_panel.buttons.start_new_game, button_panel.buttons.options]
            if option.options is not None:  # Do we need a toggle button or one to in/decrement values
                plus = Button(name='+', callback=partial(button_panel.callbacks['change_option'], adjust=1, option=option, engine_option=True), call_nr=4)
                minus = Button(name='-', callback=partial(button_panel.callbacks['change_option'], adjust=-1, option=option, engine_option=True), call_nr=5)
                buttons.append(plus)
                buttons.append(minus)
            else:  # options is None
                toggle = Button(name='Toggle', callback=button_panel.callbacks['toggle_option'], call_nr=3)
                buttons.append(toggle)

            image = FrameImage(path='images/calvin/spiff_zarg.png', pos=(260, 31))
            items = [FOOTER_LARGE, TITLE_DECORATION_LEFT, TITLE_DECORATION_RIGHT, image]
            frame = Frame(option.name, items=items, buttons=buttons)

        else:
            value = option.value
            text = FrameText(content='{0}: {1}{2}'.format(option.name, value, option.unit), pos=(15, 6), font=config.FONT_NORMAL, fill=config.WHITE)
            rectangle = FrameRectangle(measurements=(0, 0, 400, 92))
            items = [rectangle, text]
            frame = PartialFrame(name='engine set', items=items, width=400, height=92, pos=(0, 208))

    else:
        raise TypeError('Engine option should be a config.Option or config.Person type {0} {1} '.format(type(option), option))

    return frame


def main_personality_option(button_panel: button.Panel, person: config.Person) -> Frame:
    """
    frame for specific engine option: personality
    :param button_panel, dict with button.Button object
    :param person: config.Person (namedtuple)
    :return: rpi_zero.Frame or rpi_zero.PartialFrame
    """
    rectangle = FrameRectangle(measurements=(0, 190, 400, 300))
    items = [rectangle, TITLE_DECORATION_LEFT, TITLE_DECORATION_RIGHT]
    align = 15
    cursor = 105

    if person.category == 'FAMOUS':  # Famous player (Don't write down the category)
        # name
        items.append(FrameText(pos=(align, cursor), content=person.name.capitalize(), font=config.FONT_BIG))
        cursor += 20
        # country
        items.append(FrameText(pos=(align, cursor), content=textwrap.fill(person.country, width=16), spacing=4))
        if len(person.country) > 16:  # if p.country takes 2 lines
            cursor += 36
        else:
            cursor += 18

        if person.life:
            text_split = person.life.split()
            text_split[0] += '*'  # birth symbol
            if len(text_split) == 3:
                text_split[-1] += '\u2020'  # dagger, Deceased symbol

            items.append(FrameText(pos=(align, cursor), content=''.join(text_split)))

    elif person.category in ('', 'GM', 'LEAGUE', 'KID', 'FUN'):  # Other personalities
        # name
        cursor += 10
        items.append(FrameText(pos=(align, cursor), content=person.name.upper(), font=config.FONT_BIG))
        cursor += 20
        # category
        items.append(FrameText(pos=(align + 15, cursor), content=person.category.lower()))

    else:
        raise ValueError('main_personality_option: unknown config.Person.category')

    if person.image:
        # image height for famous player needs to be 120px
        image = FrameImage(path=''.join([config.RODENT_IMAGES, person.image]), pos=(210, 40))
    else:
        image = FrameImage(path=config.MAIN_PERSONALITY_IMAGE, pos=(210, 40))

    items.append(image)
    # Description
    items.append(FrameText(pos=(15, 196), content=textwrap.fill(person.description, width=33), fill=config.WHITE, spacing=4))

    plus = Button(name='+', callback=partial(button_panel.callbacks['change_option'], adjust=1, option=person, engine_option=True), call_nr=4, align=config.RIGHT)
    minus = Button(name='-', callback=partial(button_panel.callbacks['change_option'], adjust=-1, option=person, engine_option=True), call_nr=5, align=config.RIGHT)
    buttons = [button_panel.buttons.start_new_game, plus, button_panel.buttons.options, minus]
    frame = Frame('Personality', items=items, buttons=buttons)

    return frame


def main_markers(button_panel: button.Panel, setup: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    :param button_panel, dict with button.Button object
    :param setup: GAME.setup
    :param partial_frame. Set True to get the partial frame
    :return: PartialFrame or FrameArray with prefetched frame
    """
    if not partial_frame:
        toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], option=setup.markers), call_nr=3)
        buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
        frame = FrameArray('main_markers', content=frame_array.led_markers, buttons=buttons)
    else:
        setup = setup.markers.value
        text = FrameText(content='Move markers: {0}'.format('On' if setup is True else 'Off'), pos=(15, 6), fill=config.WHITE)
        rectangle = FrameRectangle(measurements=(0, 0, 200, 40))
        frame = PartialFrame(name='markers', items=[rectangle, text], width=200, height=40, pos=(0, 208))

    return frame


def main_mark_last_move(button_panel: button.Panel, setup: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    If no setup are given the function will return the FrameArray
    :param button_panel, dict with button.Button object
    :param setup: GAME.setup. Necessary in case of a partial frame
    :param partial_frame: bool. set True is frame is a partial frame
    :return: PartialFrame, FrameArray
    """
    if not partial_frame:
        toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], option=setup.mark_last_move), call_nr=3)
        buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
        frame = FrameArray('main_mark_last_move', frame_array.mark_last_move, buttons)
    else:
        setup = setup.mark_last_move.value
        content = 'Mark last move: {0}'.format('On' if setup is True else 'Off')
        text = FrameText(content=content, pos=(15, 6), fill=config.WHITE)
        rectangle = FrameRectangle(measurements=(0, 0, 224, 40))
        frame = PartialFrame(name='mark last move', items=[rectangle, text], width=224, height=40, pos=(0, 208))

    return frame


def main_wait_for_confirm(button_panel: button.Panel, setting: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    If no setup are given the function will return the FrameArray
    :param button_panel, dict with button.Button object
    :param setting: GAME.setup. Necessary in case of a partial frame
    :param partial_frame. Set True to get the partial frame
    :return: FrameArray or PartialFrame
    """
    setting = setting.wait_to_confirm
    if not partial_frame:
        toggle = (Button('Toggle', partial(button_panel.callbacks['toggle_option'], option=setting), call_nr=3))
        buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
        frame = FrameArray('main_wait_for_confirm', frame_array.wait_to_confirm, buttons)
    else:
        content = 'Confirm move with timeout: {0}'.format('Yes' if setting.value is True else 'No')
        text = FrameText(content=content, pos=(15, 6), fill=config.WHITE)
        rectangle = FrameRectangle(measurements=(0, 0, 400, 38))
        frame = PartialFrame(name='wait for confirm', items=[rectangle, text], width=400, height=38, pos=(0, 208))

    return frame


def main_defaults(button_panel: button.Panel) -> FrameArray:
    """
    Restore default setup
    :return: PartialFrame
    """
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, button_panel.buttons.restore_defaults)
    return FrameArray('main_restore_defaults', frame_array.restore_defaults, buttons)


# Game
def game_new() -> Frame:
    """
    Start new game
    :return: Frame
    """
    image = FrameImage(path='images/calvin/new_waterballoon.png', pos=(0, 50))
    items = [FOOTER, TITLE_DECORATION_RIGHT, TITLE_DECORATION_LEFT, image]
    return Frame('New GAME', items=items)


def game_player_turn(button_panel: button.Panel, content: Union[tuple, FrameItems] = None, partial_frame: bool = False) -> FrameTypes:
    """
    If there is content given the function will return it on a partial frame.
    :param button_panel, dict with button.Button object
    :param content: FrameItem for the partial frame OR tuple/list with multiple Frameitems
    :param partial_frame. Set True to get the partial frame
    :return: PartialFrame OR tuple(prefetched frame, tuple(buttons))
    """
    if not partial_frame:
        buttons = (button_panel.buttons.hint, button_panel.buttons.undo, button_panel.buttons.redo, Button('Stop', button_panel.callbacks['stop_game'], call_nr=4))
        frame = FrameArray('game_player_turn', frame_array.player_turn, buttons)

    else:
        rectangle = FrameRectangle(measurements=(0, 0, 400, 92))
        frame = PartialFrame(name='player turn', items=[rectangle], width=400, height=112, pos=(0, 208))
        if isinstance(content, (list, tuple)):
            frame.items.extend(content)
        else:
            frame.items.append(content)

    return frame


def game_validate_board(button_panel: button.Panel, message: str, current_board: chess.SquareSet, incoming_board: chess.SquareSet, game_board: chess.Board) -> Frame:
    """
    :param message: str title for the frame. Error message
    :param button_panel, dict with button.Button object
    :param current_board: chess.Squareset, containing the current chess board
    :param incoming_board: chess.Squareset
    :param game_board: chess.Board
    :return: Frame
    """
    missing = tuple(current_board.difference(incoming_board))  # missing pieces
    wrong = tuple(incoming_board.difference(current_board))  # wrong pieces
    line = []
    if missing:
        line.append('Missing:\n')
        text0 = ''.join(['{0} '.format(chess.square_name(square)) for square in missing])
        line.append(textwrap.fill(text0, width=12))
        line.append('\n')

    if wrong:
        line.append('Wrong:\n')
        text1 = ' '.join(chess.square_name(square) for square in wrong)
        line.append(textwrap.fill(text1, width=12))

    text0 = FrameText(content=make_epaper_board(game_board), pos=(-20, 25), font=config.CHESS_FONT, spacing=0)
    text1 = FrameText(content=''.join(line), pos=(265, 75))
    buttons = Button('Stop', callback=button_panel.callbacks['stop_game'], call_nr=4, align=config.RIGHT),
    return Frame(name=message, items=[text0, text1], buttons=buttons)


def game_show_board(button_panel: button.Panel, board: chess.Board) -> Frame:
    """
    Show complete board
    :param button_panel, dict with button.Button object
    :param board: chess.Board
    :return: Frame
    """
    def get_key(piece: chess.Piece) -> int:
        return piece.piece_type

    captured = [piece for piece in chess.Board().piece_map().values()]
    piece_list = [piece for piece in board.piece_map().values()]
    for piece in piece_list:
        captured.remove(piece)

    # change and sort the symbols for the chess font
    white_pieces = [piece for piece in captured if piece.color is config.WHITE]
    if white_pieces:
        white_pieces.sort(key=get_key)

    black_pieces = [piece for piece in captured if piece.color is config.BLACK]
    if black_pieces:
        black_pieces.sort(key=get_key)

    # : white_on_black_square = ('P', 'N', 'B', 'R', 'Q', 'K')
    # : black_on_black_square = ('O', 'M', 'V', 'T', 'W', 'L')
    # : white_on_white_square = ('p', 'n', 'b', 'r', 'q', 'k')
    # : black_on_white_square = ('o', 'm', 'v', 't', 'w', 'l')
    black_on_white_square = ('o', 'm', 'v', 't', 'w', 'l')
    converted_black_pieces = [black_on_white_square[chess.PIECE_TYPES.index(piece.piece_type)] for piece in black_pieces]

    white = ''.join([piece.symbol().lower() for piece in white_pieces])
    black = ''.join(converted_black_pieces)
    epaper_board = make_epaper_board(board)

    buttons = Button('Go back', callback=button_panel.callbacks['back_to_game'], call_nr=4, align=config.RIGHT),
    text0 = FrameText(content=textwrap.fill(black, width=6), pos=(236, 80), font=config.CHESS_FONT, spacing=1)
    text1 = FrameText(content=textwrap.fill(white, width=6), pos=(236, 197), font=config.CHESS_FONT, spacing=1)
    text2 = FrameText(content=epaper_board, pos=(-22, 30), font=config.CHESS_FONT, spacing=0)
    frame = Frame('Current board', items=[text0, text1, text2, TITLE_DECORATION_RIGHT, TITLE_DECORATION_LEFT], buttons=buttons)
    return frame


def question(button_panel: button.Panel, line: str = '[Insert question here]') -> Frame:
    """
    Important: When sending this frame to the commander the MAIN.ButtonPanel needs to be update manually.
    :param button_panel, list with button.Button object
    :param line: The question will be the title of the frame
    :return: Frame
    """
    image = FrameImage(path='images/calvin/balloons.png', pos=(150, 31))
    buttons = [button_panel.buttons.confirm, button_panel.buttons.cancel]
    return Frame(name=line, items=[FOOTER_LARGE, image], buttons=buttons)


def game_computer_turn(button_panel: button.Panel, move_text: Union[FrameText, Tuple[FrameText, FrameText]] = None, partial_frame: bool = False) -> FrameTypes:
    """
    :param button_panel, list with button.Button object
    :param move_text: FrameItem or more FrameItems
    :param partial_frame. Set True to get the partial frame
    :return: frames.Frame or PartialFrame
    """

    if not partial_frame:
        buttons = (Button('Stop', button_panel.callbacks['stop_game'], call_nr=2), button_panel.buttons.engine_stop)
        frame = FrameArray('game_computer_turn', frame_array.computer_turn, buttons)

    else:
        rectangle = FrameRectangle(measurements=(0, 0, 400, 92))
        buttons = Button('Stop', button_panel.callbacks['stop_game'], call_nr=2)
        button_panel.update_buttons(buttons)  # disable the 'engine stop' button
        frame = PartialFrame(name='computer turn', width=400, height=112, pos=(0, 208), items=[rectangle])
        if isinstance(move_text, tuple):
            frame.items.extend(move_text)
        else:
            frame.items.append(move_text)

    return frame


def game_computer_thinking(setup: config.Setup) -> FrameText:
    """
    String telling the computer is calculating a move for maximum x seconds
    :param setup: MAIN.GAME.setup
    :return: frames.Partialframe
    """
    movetime = setup.engine.options['movetime'].value
    return FrameText('Thinking...\n(Max {0}s)'.format(movetime), pos=(15, 0), fill=config.WHITE)


def game_engine_info(player_turn: bool, engine: config.EngineSetup) -> PartialFrame:
    """
    Text with the name and level of the engine
    :param player_turn: bool
    :param engine: config.Setup.engine
    :return: PartialFrame
    """
    content = '{0} {1}'.format(engine.name, engine.version)
    if 'level' in engine.options.keys():
        if engine.name == 'Rodent':  # The rodent engine needs exceptional treatment with it's 'personalities' instead of 'levels'
            content = '{0}\n{1}'.format(engine.name, engine.options['level'].value.name)
        else:
            content = '{0}\nlevel: {1}'.format(content, engine.options['level'].value)
            if engine.options['level'].unit:
                content = '{0}{1}'.format(content, engine.options['level'].unit)

    engine_text = FrameText(content=content, pos=(15, 3))
    return PartialFrame(name='GAME engine info', items=[engine_text], width=200, height=50, pos=((200, 120) if player_turn else (0, 118)))


def game_led_options(button_panel: button.Panel, setup: config.Setup, partial_frame: bool) -> FrameTypes:
    """
    Change led options during a game
    :return: frames.Frame
    """
    if not partial_frame:
        button0 = Button(name='Toggle markers', callback=partial(button_panel.callbacks['toggle_option'], setup=setup.markers), call_nr=1)
        button1 = Button(name='Toggle mark last move', callback=partial(button_panel.callbacks['toggle_option'], setup=setup.mark_last_move), call_nr=2)
        button2 = Button(name='Toggle wait to confirm', callback=partial(button_panel.callbacks['toggle_option'], setup=setup.wait_to_confirm), call_nr=3)
        button3 = Button(name='Go back', callback=partial(button_panel.callbacks['back_to_game']), call_nr=4)
        buttons = (button0, button1, button2, button3)
        frame = FrameArray('led_options', content=frame_array.led_options, buttons=buttons)

    else:
        text0 = FrameText(pos=(0, -20), content='\n{0}'.format('On' if setup.markers.value is True else 'Off'))
        text1 = FrameText(pos=(0, 23), content='\n{0}'.format('On' if setup.mark_last_move.value is True else 'Off'))
        text2 = FrameText(pos=(0, 63), content='\n{0}'.format('On' if setup.wait_to_confirm.value is True else 'Off'))
        frame = PartialFrame('partial_led_options', width=40, height=110, pos=(232, 43), items=[FOOTER, text0, text1, text2])

    return frame


def end_game(button_panel: button.Panel, result: str, setup: config.Setup, board: chess.Board) -> Frame:
    """
    Show result of the GAME. Ask if player wants to keep a copy of the pgn file.
    Copies are saved in the 'history' folder.
    :return: rpi_zero.Frame
    :param button_panel, list with button.Button object
    :param result: char, '*, 1/2, 1/0, 0/1
    :param setup: config.Setup
    :param board: chess.Board
    :return:
    """
    if result == '*':
        winner = ''
        image = FrameImage(path='images/calvin/playing_in_snow.png', pos=(190, 31))
    elif result[-3:] == '1/2':
        winner = 'Draw'
        image = FrameImage(path='images/calvin/slap.png', pos=(200, 31))
    elif int(result[-1]) != int(setup.color.value):
        winner = 'Player wins'
        image = FrameImage(path='images/calvin/I_won2.png', pos=(136, 35))
    else:
        winner = 'Computer wins'
        image = FrameImage(path='images/calvin/lost.png', pos=(120, 35))

    result_text = 'Result: {0}'.format(result)
    text0 = FrameText(content=result_text, pos=(5, 215), fill=config.WHITE, font=config.FONT_BIG)
    text1 = FrameText(content=winner, pos=(15, 245), fill=config.WHITE, font=config.FONT_BIGGER, align=config.CENTER)
    try:
        board.peek()
        buttons = (button_panel.buttons.confirm, Button('Save pgn', button_panel.callbacks['save_pgn'], call_nr=2))
    except IndexError:
        buttons = button_panel.buttons.confirm,

    frame = Frame('Finished!', items=[FOOTER_LARGE, text0, text1, image, TITLE_DECORATION_LEFT, TITLE_DECORATION_RIGHT], buttons=buttons)
    return frame


# ## End frames
# ----------------
# -- functions  --
# ----------------
def make_epaper_board(board: chess.Board) -> str:
    """
    Make a string to print with a chess font (chesscase.ttf). Used for the epaper screen
    :param board: chess.Board
    :returns string containing the board to be presented with a chess font

    CHESS FONT:
    DIAGRAM BORDERS:
                                          SINGLE        DOUBLE       EXTRA *
           Top left corner                  1          !  or 033     a - A
           Top border                       2          "     034
           Top right corner                 3          #     035     s - S
           Left border                      4          $     036
           Right border                     5          %     037
           Bottom left corner               7          /     047     d - D
           Bottom border                    8          (     040
           Bottom right corner              9          )     041     f - F

    BOARD POSITION ASSIGNMENTS:
                                        WHITE SQUARE         DARK SQUARE
           Squares                      [space] or * 042          +  043
           White pawn                        p                    P
           Black pawn                        o                    O
           White knight                      n                    N
           Black knight                      m                    M
           White bishop                      b                    B
           Black bishop                      v                    V
           White rook                        r                    R
           Black rook                        t                    T
           White queen                       q                    Q
           Black queen                       w                    W
           White king                        k                    K
           Black king                        l                    L
    """
    white_on_black_square = ('P', 'N', 'B', 'R', 'Q', 'K')
    black_on_black_square = ('O', 'M', 'V', 'T', 'W', 'L')
    white_on_white_square = ('p', 'n', 'b', 'r', 'q', 'k')
    black_on_white_square = ('o', 'm', 'v', 't', 'w', 'l')
    # make empty board
    output = (['!', '"', '"', '"', '"', '"', '"', '"', '"', '#', '\n',
               '$', ' ', '+', ' ', '+', ' ', '+', ' ', '+', '%', '\n',
               '$', '+', ' ', '+', ' ', '+', ' ', '+', ' ', '%', '\n',
               '$', ' ', '+', ' ', '+', ' ', '+', ' ', '+', '%', '\n',
               '$', '+', ' ', '+', ' ', '+', ' ', '+', ' ', '%', '\n',
               '$', ' ', '+', ' ', '+', ' ', '+', ' ', '+', '%', '\n',
               '$', '+', ' ', '+', ' ', '+', ' ', '+', ' ', '%', '\n',
               '$', ' ', '+', ' ', '+', ' ', '+', ' ', '+', '%', '\n',
               '$', '+', ' ', '+', ' ', '+', ' ', '+', ' ', '%', '\n',
               '/', '(', '(', '(', '(', '(', '(', '(', '(', ')'
               ])
    # iterate the piece_map from GAME.board and replace symbols with the corresponding key from the empty board
    if board is None:
        return ''.join(output)

    piece_map = board.piece_map()
    for key, piece in piece_map.items():
        index = chess.PIECE_SYMBOLS.index(piece.symbol().lower()) - 1

        # Bit of a tricky formula due to the chessboard squares represented by a 0-63 list
        if key == 0 or (key // 8 + key % 8) % 2 == 0:
            output_symbol = white_on_black_square[index] if piece.color is config.WHITE else black_on_black_square[index]
        else:
            output_symbol = white_on_white_square[index] if piece.color is config.WHITE else black_on_white_square[index]

        output_square = chess.square_mirror(key)
        # correct the key from the piece_map item to the key for the empty board
        # 12: skip top row, 3*: add 3 per row
        output[output_square + 12 + 3 * (chess.square_rank(output_square))] = output_symbol

    return ''.join(output)


def get_half_move_text(move: int, board: chess.Board) -> Tuple[FrameText, FrameText]:
    """
    Get 'half move text for commander
    :param move: square nr (0-63)
    :param board: chess.Board
    :return: tuple with 2 FrameItem: One symbol and one square name
    """
    piece = board.piece_at(move)
    symbol = chr(config.ASCII_PIECES[piece.piece_type - 1])

    text = chess.square_name(move)
    item_symbol = FrameText(content=symbol, pos=(10, -10), fill=config.WHITE, font=config.CHESS_FONT_VERY_BIG)
    item_text = FrameText(content=text, pos=(75, 6), fill=config.WHITE, font=config.FONT_VERY_BIG)
    return item_symbol, item_text


def get_move_text(move: chess.Move, board: chess.Board) -> Tuple[FrameText, FrameText]:
    """
    returns string representing the move for the commander
    :param move, chess.Move
    :param, board: chess.Board
    :return: tuple with 2 FrameItems: move and piece symbol (they have different font)
    """
    piece = board.piece_at(move.from_square).piece_type
    symbol = chr(config.ASCII_PIECES[chess.PIECE_TYPES.index(piece)])
    text = board.lan(move)

    item_symbol = FrameText(content=symbol, pos=(10, -10), fill=config.WHITE, font=config.CHESS_FONT_VERY_BIG)
    item_text = FrameText(content=text, pos=(75, 6), fill=config.WHITE, font=config.FONT_VERY_BIG)
    return item_symbol, item_text
