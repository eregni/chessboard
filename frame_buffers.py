#!/usr/bin/env python3
"""
This script generates a text file containing all the 'prefetched frames'.
'Prefetched' items are images represented as lists.
Just to save time... See bottom on script
"""
from main import *
import textwrap
import epaper
from button import Button
from epaper import FrameTypes
from typing import Tuple
from functools import partial

FILE = 'frame_array.py'
game = Game()


def make_text(name: str, buffer: tuple, comm: str) -> str:
    """
    Make string for the frame_array.py file
    :param name: str, name of the variable
    :param buffer: str, frame buffer
    :param comm: str, comment
    :return:
    """
    nm = name.lower().replace(' ', '_')
    buffer_text = textwrap.fill(str(buffer), 120)
    text = [comm, '\n', nm, ' = ', buffer_text, '\n\n\n']
    return ''.join(text)


def process_new_frame(new_frame: FrameTypes, comm: str) -> None:
    """
    Write down the given frame as a list in the frame_array.py
    :param new_frame: FrameTypes
    :param comm: str: comment
    """
    buffer = epaper.prefetch(new_frame)
    if hasattr(new_frame, 'name'):
        name = new_frame.name
        text = make_text(name, buffer, comm)
    else:
        name = comm.strip('#')
        name.strip()
        text = make_text(name, buffer, comm)
    with open(FILE, 'a') as f:
        print(text, file=f)
    print('Added frame: {0}'.format(name))


# ########
# Frames #
# ########
def menu() -> Tuple[FrameTypes, str]:
    """FRAME MAIN INFO"""
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options)
    image = epaper.FrameImage(path='images/calvin/cart.png', pos=(218, 70))
    frame = epaper.Frame(name='Menu', items=[image, epaper.FOOTER_LARGE, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT], buttons=buttons)
    comment = '# Frame MAIN info'

    return frame, comment


def color() -> Tuple[FrameTypes, str]:
    """FRAME MAIN COLOR"""
    toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], setup=game.setup.color), call_nr=3)
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
    image = epaper.FrameImage('images/calvin/staring.png', pos=(218, 50))
    comment = '# Frame MAIN color'
    frame = epaper.Frame(name='Choose color', items=[epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, epaper.FOOTER_LARGE, image], buttons=buttons)

    return frame, comment


def engine() -> Tuple[FrameTypes, str]:
    """FRAME MAIN ENGINE"""
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, button_panel.buttons.next_engine)
    comment = '# Frame MAIN engine'
    rectangle = epaper.FrameRectangle(measurements=(0, 168, 400, 300))
    frame = epaper.Frame(name='Engine', items=[rectangle, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT], buttons=buttons)

    return frame, comment


def markers() -> Tuple[FrameTypes, str]:
    """FRAME MAIN LED MARKERS"""
    toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], setup=game.setup.markers), call_nr=3)
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
    comment = '# Frame MAIN led markers'
    image = epaper.FrameImage(path='images/calvin/spiff_going_down3.png', pos=(152, 31))
    frame = epaper.Frame(name='Led markers', items=[image, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, epaper.FOOTER_LARGE], buttons=buttons)

    return frame, comment


def led_last_move() -> Tuple[FrameTypes, str]:
    """FRAME MAIN MARK LAST MOVE"""
    toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], setup=game.setup.mark_last_move), call_nr=3)
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
    comment = '# Frame MAIN mark last move'
    image = epaper.FrameImage(path='images/calvin/spiff_going_down2.png', pos=(220, 31))
    frame = epaper.Frame(name='Mark last move', items=[image, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, epaper.FOOTER_LARGE], buttons=buttons)

    return frame, comment


def wait_to_confirm() -> Tuple[FrameTypes, str]:
    toggle = Button('Toggle', partial(button_panel.callbacks['toggle_option'], setup=game.setup.wait_to_confirm), call_nr=3)
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, toggle)
    comment = '# wait_to_confirm'
    image = epaper.FrameImage(path='images/calvin/plan.png', pos=(262, 31))
    frame = epaper.Frame(name='Wait to confirm', items=[image, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, epaper.FOOTER_LARGE], buttons=buttons)

    return frame, comment


def restore_defaults() -> Tuple[FrameTypes, str]:
    """FRAME RESTORE DEFAULTS"""
    buttons = (button_panel.buttons.start_new_game, button_panel.buttons.options, button_panel.buttons.restore_defaults)
    comment = '# Frame MAIN restore defaults'
    image = epaper.FrameImage(path='images/calvin/quiet.png', pos=(212, 40))
    default_engine = config.STOCKFISH
    content = ''.join(['Engine: ', default_engine.name,
                       '\nSkill: ', str(default_engine.options['level'].value),
                       default_engine.options['level'].unit,
                       '\nMove time: ', str(default_engine.options['movetime'].value),
                       default_engine.options['movetime'].unit,
                       '\nPlayer is white'])
    rectangle = epaper.FrameRectangle(measurements=(0, 208, 212, 300))
    text = epaper.FrameText(content=content, pos=(15, 214), fill=config.WHITE)
    frame = epaper.Frame(name='Restore defaults', items=[rectangle, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, text, image], buttons=buttons)

    return frame, comment


def player_turn():
    """FRAME GAME PLAYER TURN"""
    buttons = (button_panel.buttons.hint, button_panel.buttons.undo, button_panel.buttons.redo, Button('Stop', button_panel.callbacks['stop_game'], call_nr=4, align=config.RIGHT))
    image = epaper.FrameImage(path='images/calvin/waterballoon.png', pos=(120, 31))
    frame = epaper.Frame(name='Player turn', items=[image, epaper.FOOTER_LARGE, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT], buttons=buttons)
    comment = '# Frame MAIN player turn'

    return frame, comment


def computer_turn():
    """FRAME GAME COMPUTER TURN"""
    buttons = (button_panel.buttons.engine_stop, Button('Stop', button_panel.callbacks['stop_game'], call_nr=2))
    image = epaper.FrameImage(path='images/calvin/calvin_move2.png', pos=(200, 30))
    frame = epaper.Frame(name='Computer turn', items=[image, epaper.FOOTER_LARGE, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT], buttons=buttons)
    comment = '# Frame computer turn'

    return frame, comment


def led_options():
    """FRAME GAME LED OPTIONS"""
    comment = '# Ingame led options'
    buttons = (
        Button('Go back', callback=button_panel.callbacks['back_to_game'], call_nr=4, align=config.RIGHT),
        Button('Markers', callback=partial(button_panel.callbacks['toggle_option'], setup=game.setup.markers), call_nr=1),
        Button('Last move', partial(button_panel.callbacks['toggle_option'], setup=game.setup.mark_last_move), call_nr=2),
        Button('Wait to confirm', partial(button_panel.callbacks['toggle_option'], setup=game.setup.wait_to_confirm), call_nr=3)
    )

    image = epaper.FrameImage('images/calvin/zzz.png', pos=(0, 208))
    frame = epaper.Frame(name='Led options', items=[epaper.FOOTER, epaper.TITLE_DECORATION_LEFT, epaper.TITLE_DECORATION_RIGHT, image], buttons=buttons)

    return frame, comment


# ########################################
# THIS LIST OF FRAMES WILL BE PROCESSED ##
# ########################################
frames = (
    menu,
    color,
    engine,
    markers,
    led_last_move,
    wait_to_confirm,
    restore_defaults,
    player_turn,
    computer_turn,
    led_options
)
# #########################################

# #######
# START #
# #######
with open(FILE, 'w') as file:
    file.write('# collection of prefetched framebuffers\n\n')
for frm in frames:
    process_new_frame(*frm())


print('\n{0} frames succesfully exported to {1}\n'.format(len(frames), FILE))
gpio.cleanup()
exit(0)
