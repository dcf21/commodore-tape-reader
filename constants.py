# constants.py
# -*- coding: utf-8 -*-
#
# The Python script in this file contains ASCII and Commodore BASIC lookup tables.
#
# Copyright (C) 2022-2023 Dominic Ford <https://dcford.org.uk/>
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
This file contains lookup tables for the character sets used by Acorn and Commodore computers, as well
as the BASIC tokens used by Commodore BASIC.

References:

https://www.c64-wiki.com/wiki/BASIC_token
https://en.wikipedia.org/wiki/PETSCII#Commodore_64_control_characters
"""

# Commodore display-code lookup table
cbm_display_codes = r"""@ABCDEFGHIJKLMNOPQRSTUVWXYZ[£].. !"#$%&'()*+,-./0123456789:;<=>?""" \
                    r"""@abcdefghijklmnopqrstuvwxyz[£]...ABCDEFGHIJKLMNOPQRSTUVWXYZ.....""" \
                    r"""................................................................""" \
                    r"""................................................................"""

# PETSCII lookup table (in uppercase mode)
petscii_upper = r"""................................ !"#$%&'()*+,-./0123456789:;<=>?""" \
                r"""@ABCDEFGHIJKLMNOPQRSTUVWXYZ[£]↑←🭹♠🭲🭸🭷🭶🭺🭱🭴╮╰╯🭼╲╱🭽🭾●🭻♥🭰╭╳○♣🭵♦┼🮌│π◥""" \
                r"""................................ ▌▄▔▁▏▒▕🮏◤🮇├▗└┐▂┌┴┬┤▎▍🮈🮂🮃▃🭿▖▝┘▘▚""" \
                r"""🭹♠🭲🭸🭷🭶🭺🭱🭴╮╰╯🭼╲╱🭽🭾●🭻♥🭰╭╳○♣🭵♦┼🮌│π◥ ▌▄▔▁▏▒▕🮏◤🮇├▗└┐▂┌┴┬┤▎▍🮈🮂🮃▃🭿▖▝┘▘π"""

# PETSCII lookup table (in lowercase mode)
petscii_lower = r"""................................ !"#$%&'()*+,-./0123456789:;<=>?""" \
                r"""@abcdefghijklmnopqrstuvwxyz[£]↑←🭹ABCDEFGHIJKLMNOPQRSTUVWXYZ┼🮌│🮖🮘""" \
                r"""................................ ▌▄▔▁▏▒▕🮏🮙🮇├▗└┐▂┌┴┬┤▎▍🮈🮂🮃▃✓▖▝┘▘▚""" \
                r"""🭹ABCDEFGHIJKLMNOPQRSTUVWXYZ┼🮌│🮖🮘 ▌▄▔▁▏▒▕🮏🮙🮇├▗└┐▂┌┴┬┤▎▍🮈🮂🮃▃✓▖▝┘▘🮖"""

# PETSCII control characters (C64 with C16 additions)
petscii_ctrl = {
    0x3: "stop", 0x5: "white", 0x8: "shift disable", 0x9: "shift enable", 0xD: "return", 0xE: "text mode",
    0x11: "cursor down", 0x12: "reverse on", 0x13: "home", 0x14: "del",
    0x1B: "esc", 0x1C: "red", 0x1D: "cursor right", 0x1E: "green", 0x1F: "blue",
    0x81: "orange", 0x82: "flash on", 0x83: "run", 0x84: "flash off", 0x85: "f1", 0x86: "f3", 0x87: "f5",
    0x88: "f7", 0x89: "f2", 0x8A: "f4", 0x8B: "f6", 0x8C: "f8", 0x8D: "lf", 0x8E: "graphics mode",
    0x90: "black", 0x91: "cursor up", 0x92: "rev off", 0x93: "clr",
    0x94: "insert", 0x95: "brown", 0x96: "pink", 0x97: "dark gray",
    0x98: "medium gray", 0x99: "light green", 0x9A: "light blue", 0x9B: "light gray",
    0x9C: "purple", 0x9D: "cursor left", 0x9E: "yellow", 0x9F: "cyan",
}

# ASCII lookup table
ascii = r"""................................ !"#$%&'()*+,-./0123456789:;<=>?""" \
        r"""@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz.....""" \
        r"""................................................................""" \
        r"""................................................................"""

# Commodore BASIC tokens - including all tokens used by BASIC 2.0 (C64), BASIC 3.5 (C16) and BASIC 7.0 (C128)
commodore_basic_tokens = {
    # BASIC 2.0
    0x80: "END",
    0x81: "FOR",
    0x82: "NEXT",
    0x83: "DATA",
    0x84: "INPUT#",
    0x85: "INPUT",
    0x86: "DIM",
    0x87: "READ",
    0x88: "LET",
    0x89: "GOTO",
    0x8A: "RUN",
    0x8B: "IF",
    0x8C: "RESTORE",
    0x8D: "GOSUB",
    0x8E: "RETURN",
    0x8F: "REM",
    0x90: "STOP",
    0x91: "ON",
    0x92: "WAIT",
    0x93: "LOAD",
    0x94: "SAVE",
    0x95: "VERIFY",
    0x96: "DEF",
    0x97: "POKE",
    0x98: "PRINT#",
    0x99: "PRINT",
    0x9A: "CONT",
    0x9B: "LIST",
    0x9C: "CLR",
    0x9D: "CMD",
    0x9E: "SYS",
    0x9F: "OPEN",
    0xA0: "CLOSE",
    0xA1: "GET",
    0xA2: "NEW",
    0xA3: "TAB(",
    0xA4: "TO",
    0xA5: "FN",
    0xA6: "SPC(",
    0xA7: "THEN",
    0xA8: "NOT",
    0xA9: "STEP",
    0xAA: "+",
    0xAB: "-",
    0xAC: "*",
    0xAD: "/",
    0xAE: "^",
    0xAF: "AND",
    0xB0: "OR",
    0xB1: ">",
    0xB2: "=",
    0xB3: "<",
    0xB4: "SGN",
    0xB5: "INT",
    0xB6: "ABS",
    0xB7: "USR",
    0xB8: "FRE",
    0xB9: "POS",
    0xBA: "SQR",
    0xBB: "RND",
    0xBC: "LOG",
    0xBD: "EXP",
    0xBE: "COS",
    0xBF: "SIN",
    0xC0: "TAN",
    0xC1: "ATN",
    0xC2: "PEEK",
    0xC3: "LEN",
    0xC4: "STR$",
    0xC5: "VAL",
    0xC6: "ASC",
    0xC7: "CHR$",
    0xC8: "LEFT$",
    0xC9: "RIGHT$",
    0xCA: "MID$",
    0xCB: "GO",
    # BASIC 3.5 / BASIC 7.0 only
    0xCC: "RGR",
    0xCD: "RCLR",
    0xCE: "RLUM",
    0xCF: "JOY",
    0xD0: "RDOT",
    0xD1: "DEC",
    0xD2: "HEX$",
    0xD3: "ERR",
    0xD4: "INSTR",
    0xD5: "ELSE",
    0xD6: "RESUME",
    0xD7: "TRAP",
    0xD8: "TRON",
    0xD9: "TROFF",
    0xDA: "SOUND",
    0xDB: "VOL",
    0xDC: "AUTO",
    0xDD: "PUDEF",
    0xDE: "GRAPHIC",
    0xDF: "PAINT",
    0xE0: "CHAR",
    0xE1: "BOX",
    0xE2: "CIRCLE",
    0xE3: "GSHAPE",
    0xE4: "SSHAPE",
    0xE5: "DRAW",
    0xE6: "LOCATE",
    0xE7: "COLOR",
    0xE8: "SCNCLR",
    0xE9: "SCALE",
    0xEA: "HELP",
    0xEB: "DO",
    0xEC: "LOOP",
    0xED: "EXIT",
    0xEE: "DIRECTORY",
    0xEF: "DSAVE",
    0xF0: "DLOAD",
    0xF1: "HEADER",
    0xF2: "SCRATCH",
    0xF3: "COLLECT",
    0xF4: "COPY",
    0xF5: "RENAME",
    0xF6: "BACKUP",
    0xF7: "DELETE",
    0xF8: "RENUMBER",
    0xF9: "KEY",
    0xFA: "MONITOR",
    0xFB: "USING",
    0xFC: "UNTIL",
    0xFD: "WHILE"
}
