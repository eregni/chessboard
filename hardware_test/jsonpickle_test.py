#!/usr/bin/env python3
"""Constant and configuration objects"""
import jsonpickle
import config
import yaml
import time

jsonpickle.set_preferred_backend('json')
FILE_JSON = 'test_jsonpickle.json'


def save_setup_json(setup: config.Setup):
    try:
        frozen = jsonpickle.encode(setup, indent=4)
        with open(FILE_JSON, 'w') as file:
            file.write(frozen)
    except (OSError, IOError):
        pass


def open_setup_json(path: str):
    try:
        with open(path, 'r') as file:
            frozen = file.read()
    except (OSError, IOError):
        pass
    return jsonpickle.decode(frozen)


def save_setup_yaml(setup: config.Setup) -> None:
    """
    Save setup to file
    :param setup: string: data to save
    :return: True/False --> successfull/Not successfull
    """
    try:
        with open(config.SETUPFILE, 'w') as file:
            yaml.dump(setup, file)
    except (OSError, IOError):
        raise SystemError("Problem saving yaml file")


def open_setup_yaml(path: str) -> config.Setup:
    """
    Open setup file
    :param path: string, path to file
    :return: dict with file_uci_options from file or default file_uci_options
    """
    try:
        with open(path) as file:
            data = yaml.load(file, Loader=yaml.FullLoader)

    except (FileNotFoundError, IOError):
        data = config.DEFAULT_SETUP
        with open(path, 'w') as file:
            yaml.dump(data, file)
    return data


print('Hi!')
print('Save config with json')
start = time.perf_counter()
save_setup_json(config.DEFAULT_SETUP)
print(time.perf_counter() - start)
print('save config with yaml')
start = time.perf_counter()
save_setup_yaml(config.DEFAULT_SETUP)
print(time.perf_counter() - start)
print('Load config with json')
start = time.perf_counter()
test = open_setup_json(FILE_JSON)
assert test == config.DEFAULT_SETUP
print(time.perf_counter() - start)
print('Load config with yaml')
start = time.perf_counter()
test = open_setup_yaml(config.SETUPFILE)
print(time.perf_counter() - start)
assert test == config.DEFAULT_SETUP
print("the end")
