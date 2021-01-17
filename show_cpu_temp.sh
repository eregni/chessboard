#!/bin/bash
cpu=$(</sys/class/thermal/thermal_zone0/temp)
echo -e "$((cpu/1000))\xe2\x84\x83"