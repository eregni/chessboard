#!/usr/bin/env python3
"""Script to make a file containing all uci options for each personality"""
from collections import namedtuple
import csv
import configparser
import subprocess

FILE = 'engines/rodent/rodent.uci'
Person = namedtuple('person', 'name category country life description active')
subprocess.run(['rm', FILE])
COUNT = 0
config = configparser.ConfigParser(allow_no_value=True)

for person in map(Person._make, csv.reader(open('engines/rodent/personalities_info.csv'))):
    if int(person.active) != 1:
        continue

    COUNT += 1
    print('Added: ' + str(person.name))
    config.add_section(person.name)
    with open('engines/rodent/personalities/{0}.txt'.format(person.name.replace(' ', '_')).lower()) as f:
        setting = f.readlines()

    for line in setting:
        line = line.strip('\n')
        if line.startswith(';'):
            config.set(person.name, line)
        else:
            split = line.split()
            try:
                name = split[2]
                value = split[-1]
                config.set(person.name, name, value)
            except IndexError:
                continue

with open(FILE, 'w') as f:
    config.write(f)

print('DONE')
print('Added {0} personalities'.format(COUNT))
