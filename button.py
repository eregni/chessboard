#!/usr/bin/env python3
"""
Manage the push buttons and reed switches.
Configuration for Button objects.
Make list/dict with buttons and callbacks
"""

import logging
import threading
import queue
import os
import signal
from typing import Dict, Union, List, Tuple, Callable, Any
from dataclasses import dataclass

import config
import serial_arduino
import gpio


LOG = logging.getLogger(__name__)


@dataclass
class Button:
    """Object containing variables for the physical buttons"""
    name: str
    callback: Callable
    call_nr: int
    debounce: int = config.BUTTON_DEBOUNCE
    align: int = config.LEFT

    def __str__(self) -> str:
        return '{0}: {1}'.format(type(self), self.name)

    def __repr__(self) -> str:
        return '{0}: {1}, call_nr={2}, callback={3}'.format(type(self), self.name, self.call_nr, self.callback)


class Panel:
    """ Button panel """
    def __init__(self, callbacks: Dict[str, Callable]):
        self.button_lock: threading.Lock = threading.Lock()
        self.callback_queue: queue.Queue = queue.Queue(maxsize=3)
        self.active_callbacks: list = [self.no_call] * 8
        self.wait_for_button: threading.Barrier = threading.Barrier(parties=2)
        self.move_event = threading.Barrier = threading.Event()
        self.buttons: AllButtons = AllButtons(callbacks)
        self.callbacks = callbacks

    def __str__(self) -> str:
        items = ['\n{0}'.format(item) for item in self.active_callbacks]
        return 'Panel:\n {0}'.format(items)

    def handler_callbacks(self) -> None:
        """callback function for the push button interrupts. Adds job to the button queue and triggers button event"""
        if self.button_lock.locked():
            LOG.debug('button_panel is locked. Ignoring call')
            return

        gpio.mcp23s17_write_register(gpio.GPINTENA, 0x00)  # Disable mcp23s17 interrupts
        incoming = gpio.mcp23s17_read_register(gpio.INTFA)

        if incoming not in range(0, 8):
            raise ValueError('button.Panel.handler_callbacks: Recieved invalid button nr')

        LOG.debug('Button interrupt on button %s', incoming)

        try:
            self.callback_queue.put(self.active_callbacks[incoming], timeout=1)
        except queue.Full:
            LOG.critical('button handler: Couldn\' t put new job into queue. Previous possibly stuck')

        # if program is waiting for button --> let it stop waiting and pick up task from the queue
        if self.wait_for_button.n_waiting == 1:
            self.wait_for_button.wait()  # sync with MAIN thread
            LOG.debug('wait_for_button: wait finished')
            serial_arduino.trigger_arduino_int()  # trigger reed pulse because the program was waiting for a button instead  # todo why?
        else:
            os.kill(os.getpid(), signal.SIGUSR1)  # todo what is this???

        gpio.mcp23s17_read_register(gpio.INTCAPA)
        while True:  # ensure no button is pressed anymore  # todo necessry???
            if gpio.mcp23s17_read_register(gpio.GPIOA) == 0xFF:
                break

        gpio.mcp23s17_write_register(gpio.GPINTENA, 0xFF)  # Reenable mcp23017 interrupts

    def update_buttons(self, buttons: Union[Tuple[Button], List[Button], Button]) -> None:
        """
        Assign callback functions to push buttons
        :param buttons: list with button.Button
        :return:
        """
        self.button_lock.acquire()
        self.active_callbacks = [self.no_call] * 8
        LOG.debug('Buttons got new callbacks:')
        if isinstance(buttons, Button):
            buttons = (buttons,)
        for btn in buttons:
            self.active_callbacks[btn.call_nr] = btn.callback
            LOG.debug('%s:button_panel Panel callback: %s', btn.call_nr, btn.callback)

        self.update_button_leds([btn.call_nr for btn in buttons])
        self.button_lock.release()

    @staticmethod
    def update_button_leds(leds: list) -> None:
        """
        turn on the given leds and turn off the rest
        :param leds: list containing led nrs who have to be turned ON. Other leds will be turned off
        :return:
        """
        setting = 0
        for led in leds:
            if led not in range(7):
                raise ValueError('button.Panel.update_button_leds: invalid led index')
            setting |= 1 << (6 - led)  # led connector is soldered in opposite direction :-D

        gpio.set_button_led(setting)

    def clear_butons(self):
        """Diable all buttons"""
        self.button_lock.acquire()
        self.active_callbacks = [self.no_call] * 8
        self.update_button_leds([])
        self.button_lock.release()

    def execute_task(self, signr: int = None, frame: int = None, timeout: int = None) -> Any:
        """
        Wait and execute task from buttons. When a timeout is given the program will hold until a button is pressed
        :param signr: SIGNAL nr
        :param frame: SIGNAL frame
        :param timeout: timeout in seconds
        :return:
        """
        LOG.debug('Waiting for button. Timeout = %s, signr = %s, frame = %s', timeout, signr, frame)
        result = None
        try:
            if timeout is not None:
                self.wait_for_button.wait(timeout=timeout)

            task = self.callback_queue.get(block=True, timeout=timeout)
            result = task()
        except threading.BrokenBarrierError:
            LOG.debug('wait_for_button timeout')
        except queue.Empty:
            LOG.exception('No job found in button queue! Probably a timeout')

        return result

    def wait_for_move(self, timeout: int = config.AUTOSHUTDOWN + 30):
        """
        Let the program wait for a reed event
        :param timeout: seconds
        :return: True if event has been set before timeout else False
        """
        serial_arduino.reed_on()
        self.move_event.wait(timeout=timeout)  # todo necessary???
        gpio.wait_for_arduino_int(timeout=timeout)
        serial_arduino.reed_off()

    @staticmethod
    def toggle_alarm(active: bool = True) -> None:
        """
        :param active: bool, False to turn SIGALRM off
        Alarm to save GAME and shutdown pi when program is idle"""
        if active:
            signal.alarm(config.AUTOSHUTDOWN)
            LOG.debug('Alarm set at %s seconds', config.AUTOSHUTDOWN)
        else:
            signal.alarm(0)
            LOG.debug('Alarm disabled')

    @staticmethod
    def no_call() -> None:
        """dummy"""
        LOG.debug('Button disabled, no call')


class AllButtons(list):
    """Create button objects"""
    def __init__(self, callbacks: Dict[str, Callable]):
        super().__init__()
        self.confirm = Button('Confirm', callbacks['confirm'], call_nr=1)
        self.cancel = Button('Cancel', callbacks['cancel'], call_nr=2)

        # Main menu + in GAME options
        self.start_new_game = Button('Start new game', callbacks['start_game'], call_nr=1)
        self.options = Button('Options >', callbacks['show_next_menu_item'], call_nr=2)
        self.next_engine = Button('Next engine', callbacks['show_next_engine'], call_nr=3)
        self.restore_defaults = Button('Restore defaults', callbacks['restore_defaults'], call_nr=3)
        self.back_to_game = Button('Go back', callbacks['back_to_game'], call_nr=1)

        # Player turn
        self.hint = Button('Hint', callbacks['give_hint'], call_nr=1)
        self.undo = Button('Undo', callbacks['undo'], call_nr=2)
        self.redo = Button('Redo', callbacks['redo'], call_nr=3)
        self.show_board = Button('Show board', callbacks['show_board'], call_nr=4, align=config.RIGHT)
        self.led_options = Button('Led options', callbacks['led_options'], call_nr=4, align=config.RIGHT)

        # Computer turn
        self.engine_stop = Button('Engine stop', callbacks['engine_stop'], call_nr=1)
