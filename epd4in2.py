#!/usr/bin/env python3

##
#  @filename   :   epd4in2.py
#  @brief      :   Implements for e-paper library
#  @author     :   Yehui from Waveshare
#
#  Copyright (C) Waveshare     September 9 2017
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
from time import perf_counter
import logging
from typing import Tuple, List, Union
import gpio
import config

LOG = logging.getLogger(__name__)

# Display resolution
EPD_WIDTH = config.DEVICE_WIDTH
EPD_HEIGHT = config.DEVICE_HEIGHT
COMPLETE_FRAME = EPD_WIDTH * EPD_HEIGHT

# GDEW042T2 commands
PANEL_SETTING = 0x00
POWER_SETTING = 0x01
POWER_OFF = 0x02
POWER_OFF_SEQUENCE_SETTING = 0x03
POWER_ON = 0x04
POWER_ON_MEASURE = 0x05
BOOSTER_SOFT_START = 0x06
DEEP_SLEEP = 0x07
DATA_START_TRANSMISSION_1 = 0x10
DATA_STOP = 0x11
DISPLAY_REFRESH = 0x12
DATA_START_TRANSMISSION_2 = 0x13
LUT_FOR_VCOM = 0x20
LUT_WHITE_TO_WHITE = 0x21
LUT_BLACK_TO_WHITE = 0x22
LUT_WHITE_TO_BLACK = 0x23
LUT_BLACK_TO_BLACK = 0x24
PLL_CONTROL = 0x30
TEMPERATURE_SENSOR_COMMAND = 0x40
TEMPERATURE_SENSOR_SELECTION = 0x41
TEMPERATURE_SENSOR_WRITE = 0x42
TEMPERATURE_SENSOR_READ = 0x43
VCOM_AND_DATA_INTERVAL_SETTING = 0x50
LOW_POWER_DETECTION = 0x51
TCON_SETTING = 0x60
RESOLUTION_SETTING = 0x61
GSST_SETTING = 0x65
GET_STATUS = 0x71
AUTO_MEASUREMENT_VCOM = 0x80
READ_VCOM_VALUE = 0x81
VCM_DC_SETTING = 0x82
PARTIAL_WINDOW = 0x90
PARTIAL_IN = 0x91
PARTIAL_OUT = 0x92
PROGRAM_MODE = 0xA0
ACTIVE_PROGRAMMING = 0xA1
READ_OTP = 0xA2
POWER_SAVING = 0xE3


class EPDisplay:
    """Manage the epaper screen"""
    def __init__(self):
        self._epd: _EPD = _EPD()
        self._epd.init()

    def send_to_epaper(self, frame_buffer: tuple, stamp: float = 0, partial_frame_setup: Tuple[tuple, int, int] = None,
                       full_refresh: bool = False) -> None:
        """
        Send the new image to epaper
        :param frame_buffer: tuple containing bytes to send to the epaper
        :param stamp: timestamp from perfcounter
        :param partial_frame_setup: tuple containing (x, y) coords, height and width of the partial image
        :param full_refresh: True if a full refresh is required
        """
        if partial_frame_setup:
            self._epd.set_partial_frame(frame_buffer, *partial_frame_setup)
            self._epd.display_partial_frame()
        else:
            self._epd.set_frame(frame_buffer)
            self._epd.display_frame(full_refresh=full_refresh)

        LOG.debug('timing MAIN.update_frame() --> full refresh: %s', perf_counter() - stamp)

    def clear(self, frame_buffer: Tuple[bytes] = None, full_refresh: bool = False) -> None:
        """Turn the screen complete white with an optional message in the center"""
        if frame_buffer is None:
            frame_buffer = tuple([0xFF] * (EPD_WIDTH * EPD_HEIGHT // 8))

        self._epd.set_frame(frame_buffer)
        self._epd.display_frame(full_refresh=full_refresh)

    def sleep(self):
        """Set epaper in sleep mode. This avoids uncontrolled ghosting when power gets cut off from the epaper"""
        self._epd.sleep()


class _EPD:
    """Send commands to epaper"""
    def __init__(self):
        self.reset_pin = gpio.RST_PIN
        self.dc_pin = gpio.DC_PIN
        self.busy_pin = gpio.BUSY_PIN
        self.gate = False
        self._frame_counter = config.FULL_REFRESH
        self.sleeping = False

    def reset_framecounter(self):
        """Reset frame counter"""
        self._frame_counter = config.FULL_REFRESH

    def send_command(self, command) -> None:
        """Send command to epaper IC"""
        if self.sleeping:
            self.reset()
            self.sleeping = False

        gpio.digital_write(self.dc_pin, 0)
        gpio.epaper_write(command)

    def send_data(self, data: Union[int, Tuple[bytes], List[bytes]]) -> None:
        if self.sleeping:
            self.reset()
            self.sleeping = False

        gpio.digital_write(self.dc_pin, 1)
        if isinstance(data, (tuple, list)):
            gpio.epaper_transfer_data(data)
        else:
            gpio.epaper_write(data)

    def init(self) -> None:
        self.reset()
        self.send_command(POWER_SETTING)
        self.send_data(0x03)  # VDS_EN, VDG_EN
        self.send_data(0x00)  # VCOM_HV, VGHL_LV[1], VGHL_LV[0]
        self.send_data(0x2b)  # VDH
        self.send_data(0x2b)  # VDL
        self.send_data(0xff)  # VDHR
        self.send_command(BOOSTER_SOFT_START)
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x17)  # 07 0f 17 1f 27 2F 37 2f
        self.send_command(POWER_ON)
        self.wait_until_idle()
        self.send_command(PANEL_SETTING)
        self.send_data(0x3F)  # 400x300 bw mode, LUT from REG
        self.send_command(PLL_CONTROL)
        self.send_data(0x3c)  # 3A 100HZ   29 150Hz 39 200HZ  31 171HZ
        self.send_command(RESOLUTION_SETTING)
        self.send_data(EPD_WIDTH >> 8)
        self.send_data(EPD_WIDTH & 0xff)
        self.send_data(EPD_HEIGHT >> 8)
        self.send_data(EPD_HEIGHT & 0xff)

    def wait_until_idle(self) -> None:
        timeout = 0
        while gpio.digital_read(self.busy_pin) == 0:  # 0: busy, 1: idle
            gpio.delay_ms(100)
            timeout += 1
            if timeout >= 100:
                LOG.debug("EPAPER: busy signal did not deactivate/epaper not responding in 10 sec")
                timeout = 0

    def reset(self) -> None:
        """Module reset"""
        gpio.digital_write(self.reset_pin, 1)
        gpio.delay_ms(200)
        gpio.digital_write(self.reset_pin, 0)
        gpio.delay_ms(10)
        gpio.digital_write(self.reset_pin, 1)
        gpio.delay_ms(200)

    def set_lut(self, quick: bool = False) -> None:
        self.send_command(LUT_FOR_VCOM)
        # vcom
        for count in range(0, 44):
            self.send_data(lut_vcom0_quick[count]) if quick else self.send_data(lut_vcom0[count])
        self.send_command(LUT_WHITE_TO_WHITE)
        # ww --
        for count in range(0, 42):
            self.send_data(lut_ww_quick[count]) if quick else self.send_data(lut_ww[count])

        self.send_command(LUT_BLACK_TO_WHITE)
        for count in range(0, 42):
            self.send_data(lut_bw_quick[count]) if quick else self.send_data(lut_bw[count])

        self.send_command(LUT_WHITE_TO_BLACK)
        for count in range(0, 42):
            self.send_data(lut_bb_quick[count]) if quick else self.send_data(lut_bb[count])

        self.send_command(LUT_BLACK_TO_BLACK)
        for count in range(0, 42):
            self.send_data(lut_wb_quick[count]) if quick else self.send_data(lut_wb[count])

    def set_partial_lut(self) -> None:
        self.send_command(LUT_FOR_VCOM)
        for count in range(0, 44):
            self.send_data(lut_vcom0_partial[count])

        self.send_command(LUT_WHITE_TO_WHITE)
        for count in range(0, 42):
            self.send_data(lut_ww_partial[count])

        self.send_command(LUT_BLACK_TO_WHITE)
        for count in range(0, 42):
            self.send_data(lut_bw_partial[count])

        self.send_command(LUT_WHITE_TO_BLACK)
        for count in range(0, 42):
            self.send_data(lut_wb_partial[count])

        self.send_command(LUT_BLACK_TO_BLACK)
        for count in range(0, 42):
            self.send_data(lut_bb_partial[count])

    def set_partial_frame(self, frame_buffer: Tuple[bytes], pos: tuple, height: int, width: int) -> None:
        """
        Send a partial window to SRAM
        :param frame_buffer: FrameBuffer made from the partial frame
        :param pos: int: start position of the partial frame. (x, y) coords
        :param height: int: frame heigt
        :param width: frame width
        :return:
        """
        # todo chech the partial lut from the updated waveshare module
        x = pos[0]
        y = pos[1]
        # Set display in 'partial mode'
        self.send_command(PARTIAL_IN)
        self.send_command(PARTIAL_WINDOW)

        self.send_data(x >> 8)
        self.send_data(x & 0xf8)  # x should be the multiple of 8, the last 3 bit will always be ignored
        self.send_data(((x & 0xf8) + width - 1) >> 8)
        self.send_data(((x & 0xf8) + width - 1) | 0x07)
        self.send_data(y >> 8)
        self.send_data(y & 0xff)
        self.send_data((y + height - 1) >> 8)
        self.send_data((y + height - 1) & 0xff)
        self.send_data(0x01)  # Gates scan both inside and outside of the partial window. (default 1)

        self.set_frame(frame_buffer)
        self.send_command(PARTIAL_OUT)

    def set_frame(self, frame_buffer: Tuple[bytes]) -> None:
        """
        Send frame to sram on the epaper module
        :param frame_buffer: tuple with frame buffer
        """
        self.send_command(DATA_START_TRANSMISSION_1)
        self.send_data(frame_buffer)
        self.send_command(DATA_STOP)
        gpio.delay_ms(2)

        self.send_command(DATA_START_TRANSMISSION_2)
        self.send_data(frame_buffer)
        self.send_command(DATA_STOP)
        gpio.delay_ms(2)

    def display_frame(self, full_refresh: bool = False) -> None:
        """Display frame stored in sram"""
        # TODO check the display frame commands in the new library
        LOG.debug('Display frame stored in sram')
        self.send_command(VCM_DC_SETTING)
        self.send_data(0x28)
        self.send_command(VCOM_AND_DATA_INTERVAL_SETTING)
        self.send_command(0x97)  # VBDF 17|D7 VBDW 97  VBDB 57  VBDF F7  VBDW 77  VBDB 37  VBDR B7

        if self._frame_counter == config.FULL_REFRESH or full_refresh:
            self.set_lut()
            self.send_command(DISPLAY_REFRESH)
            self.wait_until_idle()
            self.set_lut(quick=True)
            self._frame_counter = 0
        else:
            self._frame_counter += 1
            self.send_command(DISPLAY_REFRESH)
            gpio.delay_ms(200)
            self.wait_until_idle()

        LOG.debug('frame counter: %s/%s before long screen refresh', self._frame_counter, config.FULL_REFRESH)

    def display_partial_frame(self) -> None:
        # self.set_partial_lut()
        self.send_command(DISPLAY_REFRESH)
        gpio.delay_ms(200)  # THe current library from waveshere's example code tells this delay is important
        self.wait_until_idle()
        self.set_lut(quick=True)

    def sleep(self) -> None:
        """"
        After this command is transmitted, the chip would enter the
        deep-sleep mode to save power.
        The deep sleep mode would return to standby by hardware reset.
        The only one parameter is a check code, the command would be
        executed if check code = 0xA5.
        You can use reset() to awaken to initialize
         """
        self.sleeping = True
        self.send_command(0x02)  # POWER_OFF
        self.wait_until_idle()
        self.send_command(0x07)  # DEEP_SLEEP
        self.send_data(0XA5)
        # gpio.SPI_EPAPER.close()
        # gpio.GPIO.output(gpio.RST_PIN, 0)
        # gpio.GPIO.output(gpio.DC_PIN, 0)


# ########## LOOK-UP TABLES ###########
lut_vcom0 = [
    0x00, 0x17, 0x00, 0x00, 0x00, 0x02,
    0x00, 0x17, 0x17, 0x00, 0x00, 0x02,
    0x00, 0x0A, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_bw = lut_ww = [
    0x40, 0x17, 0x00, 0x00, 0x00, 0x02,
    0x90, 0x17, 0x17, 0x00, 0x00, 0x02,
    0x40, 0x0A, 0x01, 0x00, 0x00, 0x01,
    0xA0, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_wb = lut_bb = [
    0x80, 0x17, 0x00, 0x00, 0x00, 0x02,
    0x90, 0x17, 0x17, 0x00, 0x00, 0x02,
    0x80, 0x0A, 0x01, 0x00, 0x00, 0x01,
    0x50, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

# ########## LOOK-UP TABLES QUICK ###########
lut_vcom0_quick = [
    0x00, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_bw_quick = lut_ww_quick = [
    0xA0, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_wb_quick = lut_bb_quick = [
    0x50, 0x0E, 0x0E, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

# ########## LOOK-UP TABLES PARTIAL###########
lut_vcom0_partial = [
    0x00, 0x19, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, ]

lut_bb_partial= lut_ww_partial = [
    0x00, 0x19, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_bw_partial = [
    0x80, 0x19, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

lut_wb_partial = [
    0x40, 0x19, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

