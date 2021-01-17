#!/usr/bin/env python3
from main import *
from gpio import *
import button

init()
print(mcp23s17_read_register(IOCON))
print(mcp23s17_read_register(IODIRA))
print(mcp23s17_read_register(IODIRB))
print(mcp23s17_read_register(GPIOB))
print(mcp23s17_read_register(GPPUA))
print(mcp23s17_read_register(GPINTENA))
print(mcp23s17_read_register(DEFVALA))
print(mcp23s17_read_register(INTCONA))

button_panel.update_button_leds([3])
sleep(2)
button_panel.update_button_leds([])
for i in range(6, -1, -1):
    set_button_led(1 << i)
    sleep(0.5)

set_button_led(0)
sleep(1)
set_button_led(0b00111111)
print(mcp23s17_read_register(GPIOB))
print(mcp23s17_read_register(GPIOA))
sleep(2)
cleanup()
