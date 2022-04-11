cmake_minimum_required(VERSION 3.21)
project(test_an32183a)

set(CMAKE_CXX_STANDARD 14)

include_directories(.)
include_directories(print_all_registers)

add_executable(test_an32183a
        print_all_registers/print_all_registers.ino
        an32183a.cpp
        an32183a.h
        test_an32183a.ino)
