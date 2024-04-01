#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# list_commodore_basic.py
#
# This Python script produces textual listings of 8-bit Commodore BASIC files
# produced by the Commodore 64, Commodore 16, etc. It supports all the BASIC
# extensions added in the Commodore 128.
#
# Copyright (C) 2022-2024 Dominic Ford <https://dcford.org.uk/>
#
# This code is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# You should have received a copy of the GNU General Public License along with
# this file; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

# ----------------------------------------------------------------------------

"""
Produce textual listings of Commodore BASIC files. This script is compatible with all 8-bit versions of Commodore BASIC,
including BASIC 2.0 (C64), BASIC 3.5 (C16, Plus/4) and BASIC 7.0 (C128).

References:

https://www.c64-wiki.com/wiki/BASIC_token
https://en.wikipedia.org/wiki/PETSCII#Commodore_64_control_characters
"""

import argparse
import logging
import sys

from typing import Iterable

from constants import petscii_upper, petscii_ctrl, commodore_basic_tokens


def create_listing_from_file(filename: str, prg: bool):
    """
    Create a textual listing of a Commodore BASIC file.

    :param filename:
        The filename of the binary Commodore BASIC file
    :param prg:
        If true, then the input file is stored in disk PRG format, prefaced with a two-byte load address
    :return:
        string
    """

    # Read BASIC file
    with open(filename, "rb") as f:
        basic_bytes = f.read()

    # If file is in PRG format, remove two bytes of load address
    if prg:
        basic_bytes = basic_bytes[2:]

    # Produce listing
    listing = create_listing_from_bytes(byte_list=basic_bytes)

    # Return listing
    return listing


def create_listing_from_bytes(byte_list: Iterable):
    """
    Create a text listing of a Commodore BASIC file.

    :param byte_list:
        The bytes of the BASIC file
    :return:
        string
    """

    output = ""
    lines_returned = 0

    # Give up immediately if file is too short
    stream_length = len(byte_list)
    if stream_length < 5:
        output += "?FILE TOO SHORT ERROR\n"
        return output, lines_returned, True

    # The load address is used to convert the address of BASIC lines into file positions
    load_address = 256 * byte_list[1] + 1
    file_position = 0
    next_line_position = 0

    # Iterate through the file, printing the lines of BASIC code
    while True:
        bytes_remaining = stream_length - file_position

        # Fetch file position of next line of BASIC
        if bytes_remaining >= 2:
            next_line_address = byte_list[file_position] + 256 * byte_list[file_position + 1]
            if next_line_address == 0:
                return output, lines_returned, False
            next_line_position = next_line_address - load_address

        # Return an error if there's no line number
        if bytes_remaining < 5:
            output += "?FILE TRUNCATED ERROR\n"
            return output, lines_returned, True

        # Print the BASIC line number
        line_number = byte_list[file_position + 2] + 256 * byte_list[file_position + 3]
        output += "{:6d} ".format(line_number)

        # Move file position to start of line data
        file_position += 4

        # Print line, character by character
        in_quotes = False
        while file_position < stream_length:
            current_byte = byte_list[file_position]
            # A zero indicates the end of the BASIC line
            if current_byte == 0:
                break
            # Check for BASIC tokens (but not inside quotes)
            if current_byte in commodore_basic_tokens and not in_quotes:
                output += commodore_basic_tokens[current_byte]
            # Display all other characters as PETSCII
            else:
                # Render PETSCII control characters
                if current_byte in petscii_ctrl:
                    output += "<{}>".format(petscii_ctrl[current_byte])
                # Quote characters toggle whether we expand BASIC tokens
                elif current_byte == 0x22:
                    output += '"'
                    in_quotes = not in_quotes
                # All other characters rendered as PETSCII
                else:
                    output += petscii_upper[current_byte]
            file_position += 1

        # Don't allow the next line address to point backwards in the file - this can cause infinite loops!
        if next_line_position <= file_position:
            output += "\n?ILLEGAL NEXT LINE ADDRESS\n"
            return output, lines_returned, True

        # Move onto next line of BASIC code
        file_position = next_line_position
        lines_returned += 1
        output += "\n"


# Do it right away if we're run as a script
if __name__ == "__main__":
    # Set up a logging object
    logging.basicConfig(level=logging.INFO,
                        stream=sys.stdout,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.debug(__doc__.strip())

    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',
                        required=True,
                        type=str,
                        dest="input",
                        help="The Commodore BASIC file to list")
    parser.add_argument('--prg',
                        action='store_true',
                        dest="prg",
                        help="Input file is stored in disk PRG format")
    parser.set_defaults(prg=False)
    args = parser.parse_args()

    # Create listing of BASIC file
    program_listing, lines_returned, error = create_listing_from_file(filename=args.input, prg=args.prg)

    # Output listing of BASIC file to stdout
    print(program_listing)

    # Return status 1 if we didn't find a single valid line of BASIC
    if lines_returned < 1 and error:
        sys.exit(1)
    else:
        sys.exit(0)
