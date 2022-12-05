#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# commodore_tape_parse.py
#
# This Python script extracts binary files from WAV recordings of audio
# cassette tapes recorded by 8-bit Commodore computers (e.g. C64, C16,
# Plus/4 and C128). These will typically have been recorded using a
# Commodore 1530 / C2N / 1531 datasette.
#
# Copyright (C) 2022 Dominic Ford <https://dcford.org.uk/>
#
# This code is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# You should have received a copy of the GNU General Public License along with
# this file; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

# ----------------------------------------------------------------------------

"""
This Python script extracts binary files from WAV recordings of audio cassette tapes recorded by 8-bit Commodore
computers (e.g. C64, C16, Plus/4 and C128). These will typically have been recorded using a Commodore 1530 / C2N / 1531
datasette.

This script was used by the author to recover all the Commodore tapes archived on the website
<https://files.dcford.org.uk/>.

This script has been tested on files saved by Commodore 16, 64 and 128 computers. It automatically determines
the clock speed used to encode the pulses found on the tape, based on the pulse intervals found, and so can
tolerate recordings whose playback speed is significantly wrong.

By default, this script simply exports all the files to a specified output directory. If a more sophisticated export
is required, it is simple to call the <WavCommodoreFileSearch> class from an external script to perform other actions
on the files found.

Limitations:

* This script only reads files saved by the Commodore KERNAL, not turbo loading tapes (i.e. it will not read most
commercial releases, but it will read most tapes you may have recorded yourself).

* Any bit rate is supported, but >= 44.1kHz is recommended.

References:

These webpages contain a useful, though not entirely complete, guide to how the C64 stores data on tape:
https://wav-prg.sourceforge.io/tape.html
https://www.c64-wiki.com/wiki/Datassette_Encoding
https://eden.mose.org.uk/download/Commodore%20Tape%20Format.pdf
"""

import argparse
import copy
import itertools
import logging
import numpy as np
import os
import re
import sys

from functools import reduce
from operator import itemgetter
from typing import Dict, List, Sequence, Tuple

from constants import ascii, cbm_display_codes
from list_commodore_basic import create_listing_from_bytes
from wav_file_reader import WavFileReader


class WavCommodoreFileSearch:
    """
    Class to extract Commodore files from wav recordings of Commodore datasette tapes.
    """

    def __init__(self, input_filename: str):
        """
        Extract binary files from WAV recordings of Commodore datasette tapes (e.g. Commodore 64 tapes).

        :param input_filename:
            Filename of the wav file to process
        :return:
        """

        # Input settings
        self.input_filename = input_filename

        # Open wav file
        self.wav_file = WavFileReader(input_filename=self.input_filename,
                                      min_wave_amplitude_fraction=0.15)

        # List of (channel, inversion) configurations
        self.all_configs: List[Tuple[int, bool]] = list(itertools.product(range(self.wav_file.channels),
                                                                          [False, True]))

    def search_wav_file(self):
        """
        Main entry point for searching for Commodore files from a wav recording of a Commodore datasette tape.

        :return:
            List of file objects recovered
        """

        # Build a dictionary of all the chunks of data we recover with each configuration
        chunks_recovered_by_config: Dict[int, List] = {}

        # Search for files at each phase in turn
        for config_id, (channel, inversion) in enumerate(self.all_configs):
            logging.debug("Searching channel {:d} with inversion {:d}".format(channel, int(inversion)))
            chunks_recovered_by_config[config_id] = self.search_for_files(channel=channel, inversion=bool(inversion))

        # Add up total number of bytes recovered with each configuration
        bytes_by_config: Dict[int, int] = {}
        for config_id in range(len(self.all_configs)):
            bytes_recovered: int = 0
            for chunk in chunks_recovered_by_config[config_id]:
                bytes_recovered += chunk['byte_count_without_error']
            bytes_by_config[config_id] = bytes_recovered

        # Merge the chunk lists we recovered with each configuration
        sorted_config_ids: Sequence[int, int] = sorted(bytes_by_config.items(), key=itemgetter(1), reverse=True)

        # Build merged list of all the chunks we recovered with each configuration
        merged_chunk_list = []
        timing_margin = 0.1  # maximum allowed mismatch between time position of a chunk seen at different phases (sec)

        # Loop over all configurations
        for config_id in [item[0] for item in sorted_config_ids]:
            # Loop over all chunks recovered with each configuration
            for chunk in chunks_recovered_by_config[config_id]:
                # Fetch the start and end time of the chunk on the tape
                time_start = chunk['start_time']
                time_end = chunk['end_time']

                # Check if chunk has already been recovered at a previous config setting
                chunk_matches_index = None
                action = None
                for existing_chunk_index, existing_chunk in enumerate(merged_chunk_list):
                    # ... to match, the end time of the new chunk can't be before the start of the old chunk
                    if time_end < existing_chunk['start_time'] - timing_margin:
                        continue
                    # ... to match, the start time of the new chunk can't be after the end of the old chunk
                    if time_start > existing_chunk['end_time'] + timing_margin:
                        continue

                    # We have a match
                    chunk_matches_index = existing_chunk_index

                    # If this chunk failed to load successfully, and the previous instance was OK, reject the new chunk
                    if existing_chunk['pass_qc'] > chunk['pass_qc']:
                        action = None
                        break

                    # If this chunk loaded successfully, and the previous instance didn't, replace previous instance
                    if chunk['pass_qc'] > existing_chunk['pass_qc']:
                        action = "replace"
                        break

                    # If this chunk recovered more bytes than the previous instance, replace previous instance
                    if chunk['byte_count_without_error'] >= existing_chunk['byte_count_without_error']:
                        action = "replace append"
                        break

                    # If this chunk was equally as good as the previous attempt to load it, simply increment the display
                    # of which phases it was loaded at
                    action = "append"
                    break

                # We have found a new chunk
                if chunk_matches_index is None:
                    chunk['config_ids'] = [config_id]
                    merged_chunk_list.append(chunk)
                # We have found a better version of an existing chunk
                elif action == "replace":
                    chunk['config_ids'] = [config_id]
                    merged_chunk_list[chunk_matches_index] = chunk
                # We have found an equally good version of an existing chunk; update list of phases where we found it
                elif action == "append":
                    merged_chunk_list[chunk_matches_index]['config_ids'].append(config_id)
                # We have found a better version of an existing chunk, but it still didn't fully load properly
                elif action == "replace append":
                    config_ids = merged_chunk_list[chunk_matches_index]['config_ids'] + [config_id]
                    chunk['config_ids'] = config_ids
                    merged_chunk_list[chunk_matches_index] = chunk

        # Sort list of the chunks we found by start time, to create chronological index of the tape
        merged_chunk_list.sort(key=itemgetter('start_time'))

        # Return a list of all the chunk objects we recovered
        return merged_chunk_list

    def search_for_files(self, channel: int, inversion: bool):
        """
        Search for Commodore files in a WAV audio stream, using a particular audio channel (left/right), and either
        inverted, or not. Different tapes load better with different settings, due to the differing analogue audio
        chain the signal has traversed, which can introduce phase shifts. To maximise the number of files
        recovered, it is best to try all possibilities in turn.

        :param channel:
            Number of audio channel (left/right), from 0 to <self.wav_file.channels>, to search
        :param inversion:
            Boolean flag indicating whether to invert the audio stream before searching
        :return:
            List of file objects
        """

        # Select which audio channel to search
        self.wav_file.select_channel(channel=channel)
        # self.wav_file.apply_high_pass_filter(cutoff=100)  # Apply high-pass filter

        # Fetch list of downward zero-crossing times of wav file.
        zero_crossing_times = self.wav_file.fetch_zero_crossing_times(invert_wave=inversion)

        # Make list of pulse times and lengths.
        # A pulse is defined as the time interval spanned by a single wave cycle, measured from one downward zero
        # crossing to the next. Commodore tapes encode binary bits as pairs of pulses.
        pulse_list = self.wav_file.fetch_pulse_list(input_events=zero_crossing_times)

        # Analyse spectrum of pulse durations, and decide on thresholds for categorising pulses as short, medium or long
        pulse_list = self._normalise_pulse_list(pulse_list=pulse_list)

        # Assign a pulse type to each pulse - either short, medium or long
        categorised_pulse_list = self._categorise_pulse_list(pulse_list=pulse_list)

        # Turn list of pulses into list of bytes - bits are encoded as pairs of pulses, either SM or MS
        byte_list = self._parse_pulse_list(pulse_list=categorised_pulse_list)

        # Turn stream of bytes into a list of continuous blocks of data where we remained synchronised to bit stream
        chunk_list = self._parse_byte_list(byte_list=byte_list)

        # Write a textual summary of the list of the chunks we found
        # chunk_description = self.write_list_of_chunks(chunk_list=chunk_list)
        # logging.info(chunk_description)

        # Describe the detailed contents of the chunks we found
        # chunk_description = self.describe_chunks(chunk_list=chunk_list)
        # logging.info(chunk_description)

        # Write debugging output
        # self._write_debugging(pulse_list=categorised_pulse_list, byte_list=byte_list)

        return chunk_list

    @staticmethod
    def _normalise_pulse_list(pulse_list: List):
        """
        Normalize the list of pulses (periods between downward zero-crossings of the tape waveform) by converting their
        lengths from seconds into a number of computer clock cycles. We empirically estimate the clock speed based on
        the pitch of the header tone, and so it doesn't matter if the playback speed in the wav file is somewhat wrong.

        :param pulse_list:
            Input list of pulses derived from <__fetch_pulse_list>
        :return:
            A list of dictionaries describing the intervals.
        """

        # The number of seconds of tape corresponding to one clock cycle. We define a clock cycle as 1/200 of the
        # header tone frequency
        tape_clock_period = None

        # Time point in the tape when we last made a measurement of the clock frequency.
        last_clock_update_time = None

        # Loop through the wave cycles found on the tape, looking for header tones ...
        # ... as we do this, we also populate the 'length' metadata field on each cycle, with the pulse length in clock
        # cycles, based on the frequency of the most recent header tone.
        for index, item in enumerate(pulse_list):
            # Boolean flag indicating whether we have made a new estimate of the clock frequency on this pulse
            updated_clock = False
            # Only check for a header tone once every 100 samples (this is slow, and header tones should be long)
            if index % 100 == 0:
                # If we have a continuous tone, use that to adjust the assumed clock period
                # Test if next 500 samples have a very consistent period
                test_header = [item['length_sec'] for item in pulse_list[index: index + 500]]
                header_mean_period = np.mean(test_header)
                header_std_dev_period = np.std(test_header)
                # ... if the standard deviation of the next 500 wave cycles is less than 2.5%, it looks like a header
                if header_std_dev_period < header_mean_period * 0.025:
                    # Normalise the frequency of the header tone to 200 clock cycles per wave cycle
                    new_tape_clock_period = header_mean_period / 200

                    # Reject this clock change if it is very similar to existing clock period (don't produce endless
                    # messages about clock updates for no reason).
                    fractional_clock_change = 1
                    if tape_clock_period is not None:
                        fractional_clock_change = abs(new_tape_clock_period - tape_clock_period) / new_tape_clock_period

                    # Only update the clock if the change is more than 2%, or we've gone 10 sec since last update
                    if ((last_clock_update_time is None) or (fractional_clock_change > 0.02) or
                            (item['time'] - last_clock_update_time > 10)):
                        updated_clock = True
                        tape_clock_period = new_tape_clock_period
                        last_clock_update_time = item['time']
                        logging.debug("[{:10.5f}] Updated clock period to {:.6f} ms; std={:.6f}".format(
                            item['time'], tape_clock_period * 1e3, header_std_dev_period / header_mean_period))

            # If we have previously encountered a header tone and estimated the clock frequency, use that to
            # convert the length of each pulse (in seconds) to a length in clock cycles
            if tape_clock_period is None:
                pulse_cycles = 0
            else:
                pulse_cycles = round(item['length_sec'] / tape_clock_period)

            # Update the descriptor for each pulse with a normalised duration in clock cycles
            item['length'] = pulse_cycles  # Length of pulse in clock cycles
            item['clock_updated'] = updated_clock  # Boolean flag indicating a new clock frequency measurement

        # Return pulse list, with the 'length' and 'clock_updated' fields populated on each pulse.
        return pulse_list

    def _categorise_pulse_list(self, pulse_list: List):
        """
        Populate the list of pulses (wave cycles) with a categorisation of each pulse as either short, medium, or long.
        Commodore tapes encode binary bits by pairs of pulses - either S, M; or M, S. In theory, the populations of
        short, medium and long pulses should have very distinct populations of periods. In practice, these populations
        can be a bit blurred.

        :param pulse_list:
            Input list of pulses derived from <fetch_pulse_list> and normalised by <_normalise_pulse_list>.
        :return:
            A list of dictionaries describing the intervals.
        """

        # Analyse the histogram of pulse lengths in the first data block on the tape, to estimate the best initial
        # threshold lengths to use for S, M, L pulses
        pulse_types = self._analyse_pulse_length_histogram(pulse_list=pulse_list, start_index=0)

        # Start building a histogram of the types of pulses we've found on the tape. This is not necessary, but it's
        # useful for diagnostics.
        default_pulse_type_histogram = {'?': 0, 's': 0, 'm': 0, 'l': 0, '<': 0, '>': 0}

        # Create a new initial pulse type histogram
        pulse_type_histogram = default_pulse_type_histogram.copy()

        # Cycle through the entire tape, categorising all the pulses (wave cycles) as S, M or L
        for index, item in enumerate(pulse_list):
            # If we hit a header tone / an updated clock frequency, then do a new histogram analysis to determine
            # the best thresholds to use for S, M and L pulses
            if item['clock_updated']:
                logging.debug("Pulse type histogram: {}".format(repr(pulse_type_histogram)))
                pulse_type_histogram = default_pulse_type_histogram.copy()
                pulse_types = self._analyse_pulse_length_histogram(pulse_list=pulse_list, start_index=index)

            # See which category this pulse falls into. If it doesn't fall into any category, label it as ?
            pulse_cycles = item['length']
            pulse_type = '?'
            for candidate_pulse_type, candidate_pulse_spec in pulse_types.items():
                if candidate_pulse_spec['min'] <= pulse_cycles <= candidate_pulse_spec['max']:
                    pulse_type = candidate_pulse_type
                    break

            # Record the pulse categorisation in the 'type' metadata field
            item['type'] = pulse_type

            # Move on to the next wave cycle on the tape
            pulse_type_histogram[pulse_type] += 1

        # Log the histogram of types of pulse
        logging.debug("Pulse type histogram: {}".format(repr(pulse_type_histogram)))

        # Return pulse list, now with the 'type' field populated on each pulse.
        return pulse_list

    @staticmethod
    def _analyse_pulse_length_histogram(pulse_list: List, start_index: int):
        """
        Analyse the histogram of the lengths of pulses within a data block to determine the most likely break points
        between short, medium and long pulses. The break points are placed in the largest gaps in the histogram, as
        their ought to be a clear difference between the longest short pulse and the shortest medium pulse, etc.

        :param pulse_list:
            Input list of pulses derived from <fetch_pulse_list> and normalised by <_normalise_pulse_list>.
        :param start_index:
            The index within the pulse list where we start constructing a histogram
        :return:
            A dictionary describing the threshold lengths for S, M and L pulses.
        """

        # Calculate the time point on the tape where we start our analysis
        start_time_sec = pulse_list[start_index]['time']

        # Default pulse boundaries to use (these are based on C16 tapes)
        s_min = 100.
        m_min = 300.
        l_min = 470.
        l_max = 900.

        # Measure extent of block until next clock change. We only analyse the sequence of wave cycles until the clock
        # change - i.e. until the next header tone.
        end_index = start_index + 1
        # The flag 'clock_updated' indicates a header tone and a new clock frequency determination
        while end_index < len(pulse_list) and not pulse_list[end_index]['clock_updated']:
            end_index += 1

        # Only proceed if we have more than 1000 wave cycles (no valid data block can have less than this!)
        sample_count = end_index - start_index
        if sample_count > 1000:
            # Make histogram of pulse lengths
            histogram = [0] * 850  # 850 histogram bins, each 1 clock-cycle wide
            for item in pulse_list[start_index: end_index]:
                if 0 < item['length'] < len(histogram):
                    histogram[item['length']] += 1

            # Normalise histogram so that all the bins add to one
            histogram = [item / sample_count for item in histogram]

            # Look for long strings of poorly-populated bins in the histogram
            h_index = int(s_min)  # Index within the histogram as we scan through. We start at 100.
            zero_strings = []  # Dictionaries describing each string of zeros
            threshold = 1e-3  # Bins are defined as poorly populated if they are below this weight

            # Cycle through the histogram, bin by bin
            while h_index < len(histogram):
                # This bin is poorly populated if it's below the threshold occupation
                if histogram[h_index] < threshold:
                    # Scan rightwards through the histogram to find the next bin that is well populated
                    h_start = h_index
                    while h_index < len(histogram) and histogram[h_index] < threshold:
                        h_index += 1
                    h_end = h_index
                    # We have found a gap, from h_start to h_end.
                    # But don't include the long gap at the top of the histogram
                    if h_end < len(histogram):
                        # Add a dictionary to <zero_strings> describing this gap in the histogram
                        string_length = h_end - h_start
                        string_center = (h_start + h_end) / 2
                        # We assign a 'weight' to each gap - broadly its length, but with a slight bias towards shorter
                        # time intervals (the long pulses can have quite variable lengths, and we don't care about that)
                        string_weight = string_length / (string_center + 250)
                        zero_strings.append({
                            'start': h_start,
                            'end': h_end,
                            'length': string_length,
                            'center': string_center,
                            'weight': string_weight
                        })
                # Move rightwards looking for the next gap in the histogram.
                # If we found a gap, then continue from the far end of the gap
                h_index += 1

            # Look for three longest strings of poorly-populated bins, with a slight bias towards shorter intervals
            if len(zero_strings) > 3:
                # Sort the gaps in the histogram by weight
                zero_strings.sort(key=itemgetter('weight'), reverse=True)
                # We take the longest three gaps to be the break-points to the left of S, M and L peaks of histogram
                zero_strings = zero_strings[:3]
                zero_strings.sort(key=itemgetter('start'), reverse=False)
                # Take the center-points of these three gaps as the thresholds to use
                s_min = zero_strings[0]['center']
                m_min = zero_strings[1]['center']
                l_min = zero_strings[2]['center']
            # If debugging, dump the full histogram for the user to peer at if they want to do diagnostics
            logging.debug("[{:10.5f}] Pulse length histogram: {}".format(start_time_sec, repr(histogram)))

        # Print a status message about the new thresholds we have adopted
        logging.debug("[{:10.5f}] Updated S/M/L breakpoints: {:.0f}, {:.0f}, {:.0f}, based on {:d} samples".
                      format(start_time_sec, s_min, m_min, l_min, sample_count))

        # Dictionary of the different kinds of pulses (wave cycles) that we may find on the type, together with the
        # minimum and maximum allowed lengths for each kind of pulse
        pulse_types = {
            '<': {'min': 0, 'max': s_min},  # pulse too short to be anything
            's': {'min': s_min, 'max': m_min},  # {'min': 0x24, 'max': 0x36} -- typical S lengths, indicated online
            'm': {'min': m_min, 'max': l_min},  # {'min': 0x37, 'max': 0x49} -- typical M lengths, indicated online
            'l': {'min': l_min, 'max': l_max},  # {'min': 0x4a, 'max': 0x64} -- typical L lengths, indicated online
            '>': {'min': l_max, 'max': 1e9}  # pulse too long to be anything
        }

        # Return the dictionary of different kinds of pulse in this data block
        return pulse_types

    @staticmethod
    def _parse_pulse_list(pulse_list: List):
        """
        Take a list of wave cycles (pulses) which have been categorised as short, medium or long - and try to extract
        a stream of bytes from the wave pulses.

        :param pulse_list:
            List of pulses to parse
        :return:
            A list of all the bytes on the entire tape, each described by a dictionary.
        """

        position = 0  # Current position index in the list of pulses
        byte_start_time = 0  # Time stamp of the start of the byte we're currently assembling
        bit_list = None  # Buffer of bits we're trying to assemble into a byte

        # List of bytes we found on the tape, each having a value, and timestamp, and flag indicating whether sync was
        # lost (making this the first byte of a new data block).
        byte_list = []

        seen_break = True  # Was the last pair invalid? If so, don't report further invalid pairs until we regain sync
        sync_lost = False  # Have we recovered at least one valid byte, with no invalid pulses since?

        # Loop through the entire tape, analysing each pulse in turn
        while position < len(pulse_list) - 1:
            # Process pulse pair
            pulse_time = pulse_list[position]['time']
            pulse_pair = pulse_list[position]['type'] + pulse_list[position + 1]['type']

            # The sequence LM signifies the start of a new byte (also accept LL)
            if pulse_pair == 'lm' or pulse_pair == 'll':
                logging.debug("[{:10.5f}] Start byte".format(pulse_time))
                byte_start_time = pulse_time
                bit_list = []  # Flush buffer for assembling a new byte
            # Also accept MM as the possible start of a new byte (but only if we're not synchronised)
            elif pulse_pair == 'mm' and bit_list is None:
                logging.debug("[{:10.5f}] Start byte (long truncated)".format(pulse_time))
                byte_start_time = pulse_time
                bit_list = []
            # The sequence LS signifies the end of a byte
            elif pulse_pair == 'ls':
                logging.debug("[{:10.5f}] End byte".format(pulse_time))
                bit_list = None
            # The sequence SM indicates a bit with value 0
            elif pulse_pair == 'sm':
                logging.debug("[{:10.5f}] Bit 0".format(pulse_time))
                if bit_list is not None:
                    bit_list.append(0)
            # The sequence MS indicates a bit with value 1
            elif pulse_pair == 'ms':
                logging.debug("[{:10.5f}] Bit 1".format(pulse_time))
                if bit_list is not None:
                    bit_list.append(1)
            # If we see the sequence SS or MM, then the pair is corrupted. Infer its most likely value - either SM or
            # MS - by which pulse was the longer of the two.
            elif (pulse_pair == 'ss' or pulse_pair == 'mm') and (bit_list is not None) and (len(bit_list) < 9):
                if pulse_list[position]['length'] < pulse_list[position + 1]['length']:
                    logging.debug("[{:10.5f}] Bit 0 - recovered".format(pulse_time))
                    if bit_list is not None:
                        bit_list.append(0)
                elif pulse_pair == 'ms':
                    logging.debug("[{:10.5f}] Bit 1 - recovered".format(pulse_time))
                    if bit_list is not None:
                        bit_list.append(1)
            # If we saw an invalid pair, then we're no longer synchronised with the data stream.
            else:
                # Invalid pair; step through pulses until we get a valid pair
                if not seen_break:
                    logging.debug("--- Illegal pair <{}>".format(pulse_pair))
                    seen_break = True
                    bit_list = None
                position += 1
                sync_lost = True
                continue

            # See if we've got a byte
            # If <bit_list> contains nine bits, then that is eight binary bits plus a parity check-bit
            if bit_list is not None and len(bit_list) == 9:
                byte_value = sum([bit_list[i] * pow(2, i) for i in range(8)])
                expected_check_bit = sum([bit_list[i] for i in range(8)]) % 2
                check_bit = 1 - bit_list[8]
                check_ok = check_bit == expected_check_bit
                # Append the recovered byte to the stream of bytes in <byte_list>
                byte_list.append({
                    'time': byte_start_time,
                    'byte': byte_value,
                    'check_bit_ok': check_ok,
                    'sync_lost': sync_lost
                })
                # Empty the bit assembly buffer
                sync_lost = False
                bit_list = None
                # If we're producing debugging output, write a message about the byte we got
                logging.debug("[{:10.5f}] Byte: {:02x} [{:s}{:s}] [{:s}]".format(
                    byte_start_time, byte_value, ascii[byte_value], cbm_display_codes[byte_value],
                    "PASS" if check_ok else "FAIL"))

            # Update status
            seen_break = False
            position += 2

        # Output list of all the bytes on the entire tape, each described by a dictionary.
        return byte_list

    @staticmethod
    def _parse_byte_list(byte_list: List):
        """
        Break up the complete stream of all the bytes found on the entire tape into chunks (blocks), each containing
        a file headers or a file itself - assuming the tape is valid!

        :param byte_list:
            The list of bytes to parse into chunks of data
        :return:
            A list of chunks/blocks of data we found, each described by a dictionary of properties
        """

        # List of all the data chunks / blocks we have found on the tape
        output_chunk_list = []

        # Flag indicating whether we're reading a valid data stream, started with the countdown bytes of either
        # $84 / $83 / $82 / $81 (indicating the first copy of a block), or $04 / $03 / $02 / $01 (indicating the second
        # duplicate copy).
        synchronised = False

        # Dictionary describing each block of data we find on the tape
        blank_chunk_descriptor = {
            'copy': 0,  # This is the first (0) or second (1) copy of this block
            'bytes': [],  # Create a new empty buffer for the contents of the block
            'byte_count': 0,  # Count the number of bytes in this block
            'byte_count_without_error': 0,  # Count the number of error-free bytes in this block
            'error_count': 0,  # Count the number of check-bit fails in this block
            'start_time': 0,
            'end_time': 0,
            'config_ids': 0
        }
        current_chunk = copy.deepcopy(blank_chunk_descriptor)

        # Cycle through the bytes on the tape, one by one, assembling bytes into blocks
        for item in byte_list:
            # Start a new chunk if we've lost synchronisation (or had a delay longer than 0.1 seconds)
            if item['sync_lost'] or item['time'] > current_chunk['end_time'] + 0.1:
                synchronised = False
                current_chunk = copy.deepcopy(blank_chunk_descriptor)
                current_chunk['start_time'] = item['time']
                current_chunk['end_time'] = item['time']

            # Feed the current byte into current chunk
            current_chunk['bytes'].append(item['byte'])
            current_chunk['end_time'] = item['time']
            if not item['check_bit_ok']:
                # If we had a check-bit error, increment the count of errors in this data chunk
                current_chunk['error_count'] += 1

            # Have we just seen a sequence of synchronisation bytes (only look if we're not already synchronised)
            if not synchronised:
                # If we see the byte sequence $84 $83 $82 $81, this indicates the start of the first copy of a block
                if current_chunk['bytes'][-4:] == [0x84, 0x83, 0x82, 0x81]:
                    # Start recording bytes into a new, empty, chunk descriptor
                    synchronised = True
                    current_chunk = copy.deepcopy(blank_chunk_descriptor)
                    current_chunk['copy'] = 0
                    current_chunk['start_time'] = item['time']
                    current_chunk['end_time'] = item['time']

                    # Append this block to the list of block we will return from this function
                    output_chunk_list.append(current_chunk)
                # If we see the byte sequence $04 $03 $02 $01, this indicates the start of the second copy of a block
                if current_chunk['bytes'][-4:] == [0x04, 0x03, 0x02, 0x01]:
                    # Start recording bytes into a new, empty, chunk descriptor
                    synchronised = True
                    current_chunk = copy.deepcopy(blank_chunk_descriptor)
                    current_chunk['copy'] = 1
                    current_chunk['start_time'] = item['time']
                    current_chunk['end_time'] = item['time']

                    # Append this block to the list of block we will return from this function
                    output_chunk_list.append(current_chunk)

        # Cycle through all the blocks of data we found on the tape, and check whether the checksums are valid
        for item in output_chunk_list:
            # If data chunk had zero bytes, add a fake check byte that will always fail
            if len(item['bytes']) == 0:
                item['bytes'] = [0, 0xff]

            # Extract the final byte from the data block, which is the checksum byte
            item['recorded_checksum'] = item['bytes'].pop()

            # Calculated expected value of check byte: it is simply found by passing all the bytes through XOR.
            if len(item['bytes']) > 0:
                item['calculated_checksum'] = reduce(lambda i, j: int(i) ^ int(j), item['bytes'])
            else:
                item['calculated_checksum'] = 0

            # Check whether this block has the correct checksum byte
            item['pass_qc'] = (item['error_count'] == 0) and (item['recorded_checksum'] == item['calculated_checksum'])

            # Populate the 'length' metadata field with the number of bytes in the block
            item['length'] = len(item['bytes'])
            item['byte_count'] = item['length']
            item['byte_count_without_error'] = item['length'] if item['pass_qc'] else 0

            # Create a hexadecimal hash for the contents of this block; we use this to easily check whether blocks
            # are exact duplicates.
            item['chunk_hash'] = abs(hash(tuple(item['bytes']))) % 0xffffff

            # Does this chunk look like a header block or a data block?
            # Don't bother categorising blocks that had read errors
            item['type'] = '----'
            if item['pass_qc']:
                # Blocks of length $C0 bytes are probably headers
                if item['length'] == 0xc0:
                    if item['bytes'][0] == 2:
                        item['type'] = 'SEQ_'
                    else:
                        item['type'] = 'HEAD'
                # Blocks of any other length probably contain a data payload
                else:
                    item['type'] = 'DATA'

        # Return list of all the blocks of data we found on the tape, each described by a dictionary of properties
        return output_chunk_list

    def write_list_of_chunks(self, chunk_list: List):
        """
        Output human-readable text describing all the blocks of data we found on the tape, and whether the checksums /
        check-bits in each block were OK.

        :param chunk_list:
            List of chunks of data (headers and files) found on the tape, as returned by <_parse_byte_list>
        :return:
            String containing a human-readable table of blocks we found
        """

        # Start building string output
        output = ""

        # Write column headings
        output += "[{:10s} - {:10s}] {:12s} {:4s} [{:6s}] {:6s}      {}\n".format(
            "Start/sec", "End/sec", "Copy  Length", "Type", "Config", "Hash", "Information"
        )

        # Write list of chunks we found
        for item in chunk_list:
            suffix = ""

            # Make an indication of which configurations recovered this file
            config_indicator = ""
            for config_id in range(len(self.all_configs)):
                if config_id in item['config_ids']:
                    config_indicator += "ABCDEFGH"[config_id]
                else:
                    config_indicator += "-"

            # For header chunks, append a suffix with the filename from the header
            if item['type'] == "HEAD":
                filename = "".join(cbm_display_codes[byte] for byte in item['bytes'][5:]).strip()
                suffix = "; type <{:02x}> filename <{}>".format(item['bytes'][0], filename)

            # For sequential data, append a suffix showing the payload
            elif item['type'] == "SEQ_":
                payload = "".join(cbm_display_codes[byte] for byte in item['bytes'][5:]).strip()
                suffix = "; type <{:02x}> payload {:d} bytes".format(item['bytes'][0], len(payload))

            # Write line of information about this chunk of data
            output += "[{:10.5f} - {:10.5f}] {:01d} {:04x} bytes {} [{:6s}] {:06x} hash{}\n".format(
                item['start_time'], item['end_time'], item['copy'], len(item['bytes']),
                item['type'], config_indicator, item['chunk_hash'], suffix
            )

        # Return output string
        return output

    @staticmethod
    def extract_files(chunk_list: List, output_dir: str):
        """
        Write all the files we extracted from the tape into an output directory.

        :param chunk_list:
            List of chunks of data (headers and files) found on the tape, as returned by <_parse_byte_list>.
        :param output_dir:
            The directory in which to save the output files
        :return:
            None
        """

        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        extracted_file_index = 0

        # Handler used to write each file
        def write_file(item_filename, item_bytes, file_index: int):
            # Create a safe version of the filename, with illegal characters removed, and /s turned into \s
            # Also append an index to the start of the filename, since tapes commonly have multiple files with the
            # same name
            item_filename_safe = ("{:02d}_".format(file_index) +
                                  re.sub('/', r'\\', item_filename.encode('utf-8', errors='replace').decode('utf-8')))

            # Turn dots into "_dot_", since we can't save files called . or ..
            output_file = os.path.join(output_dir, item_filename_safe)

            # Create file
            with open(output_file, "wb") as file_handle:
                if isinstance(item_bytes, str):
                    file_handle.write(item_bytes.encode('utf-8', errors='replace'))
                else:
                    new_file_byte_array = bytearray(item_bytes)
                    file_handle.write(new_file_byte_array)

        # Loop over each chunk on the tape in turn
        latest_filename = "<untitled>"
        last_copy_zero_hash = None
        seq = ""  # Buffer we use to collect data from SEQ files, which arrive as a string of headers containing data
        for item in chunk_list:
            # Filter out duplicate copies (all data is stored twice on a Commodore tape)
            if item['copy'] == 1 and item['chunk_hash'] == last_copy_zero_hash:
                continue
            if item['copy'] == 0:
                last_copy_zero_hash = item['chunk_hash']

            # Ignore chunks with read errors
            if item['type'] not in ("HEAD", "DATA", "SEQ_"):
                continue

            # If chunk is a HEADer, it is either a filename, or some SEQ data
            if item['type'] == "HEAD":
                filename = "".join(cbm_display_codes[byte] for byte in item['bytes'][5:]).strip()

                # If SEQ buffer contains data, save that before proceeding
                if len(seq) > 0:
                    write_file(item_filename=latest_filename, item_bytes=seq, file_index=extracted_file_index)
                    extracted_file_index += 1

                # Save the new filename we've just received
                latest_filename = filename
                seq = ""

            # If chunk is sequential data, it contains a chunk of ASCII data
            elif item['type'] == "SEQ_":
                payload = "".join(cbm_display_codes[byte] for byte in item['bytes'][5:]).strip()
                seq += payload

            # If chunk is DATA, then it is a file
            else:
                if len(seq) > 0:
                    # If SEQ buffer contains data, save that before proceeding
                    write_file(item_filename=latest_filename, item_bytes=seq, file_index=extracted_file_index)
                    extracted_file_index += 1
                    latest_filename = "<untitled>"

                # Save the file we've just found
                write_file(item_filename=latest_filename, item_bytes=item['bytes'], file_index=extracted_file_index)
                extracted_file_index += 1
                latest_filename += "_"  # Add an underscore if we find another version of this file
                seq = ""

        # Write final SEQ chunk, if one exists
        if len(seq) > 0:
            # If SEQ buffer contains data, save that before proceeding
            write_file(item_filename=latest_filename, item_bytes=seq, file_index=extracted_file_index)
            extracted_file_index += 1

    @staticmethod
    def describe_chunks(chunk_list: List):
        """
        Generate detailed textual information about the contents of each block of data we found on the tape.

        :param chunk_list:
            List of chunks of data (headers and files) found on the tape, as returned by <_parse_byte_list>.
        :return:
            String containing human-readable diagnostic information about each block of data.
        """

        # Start building output string
        output = ""

        # Keep track of the hash of the previous data block. If we see a second block with the same hash, skip over it.
        # It is normal for Commodore tapes to record every block of data twice.
        previous_hash = "xxx"

        # Loop over the blocks we found, describing them one by one
        for item in chunk_list:
            # See if this chunk is a duplicate of the previous chunk
            this_hash = "{}{}".format(item['type'], item['chunk_hash'])
            if this_hash == previous_hash:
                # ... if so, then skip over it
                continue
            previous_hash = this_hash

            # Display information about this chunk
            if item['type'] == "HEAD":
                # For HEADER blocks, decode the fields in the header
                file_type = item['bytes'][0]
                load_addr = item['bytes'][1] + 256 * item['bytes'][2]
                end_addr = item['bytes'][3] + 256 * item['bytes'][4]
                length = end_addr - load_addr
                filename = "".join(cbm_display_codes[byte] for byte in item['bytes'][5:]).strip()
                output += "# -- HEADER --\n"
                output += "# Filename    : {}\n".format(filename)
                output += "# File type   : {:02x}\n".format(file_type)
                output += "# Load address: {:04x}\n".format(load_addr)
                output += "# End address : {:04x}\n".format(end_addr)
                output += "# Length      : {:04x}\n".format(length)
            elif item['type'] == "SEQ_":
                file_type = item['bytes'][0]
                length = len(item['bytes'])
                output += "# -- SEQ --\n"
                output += "# File type   : {:02x}\n".format(file_type)
                output += "# Length      : {:04x}\n".format(length)
            elif item['type'] == "DATA":
                # For DATA blocks, attempt to LIST them as BASIC programs, if possible
                length = len(item['bytes'])
                output += "# -- DATA --\n"
                output += "# Length      : {:04x}\n".format(length)
                output += "\n{}\n".format(create_listing_from_bytes(byte_list=item['bytes']))

        # Return output
        return output

    @staticmethod
    def _write_debugging(pulse_list: List, byte_list: List):
        """
        Write a bunch of verbose debugging files to </tmp> describing the analysis of this WAV file. This is only
        useful for in-depth diagnostics.

        :param pulse_list:
            List of pulses found in file
        :param byte_list:
            List of bytes found in file
        :return:
            None
        """
        # Output pulses
        with open('/tmp/c64_pulse_lengths.txt', 'wt') as f:
            for item in pulse_list:
                f.write("{:10.5f} {:8.0f} {}\n".format(item['time'], item['length'], item['type']))

        # Output bytes
        with open('/tmp/c64_bytes.txt', 'wt') as f:
            for item in byte_list:
                byte_time = item['time']
                byte_value = item['byte']

                status = "OK"
                if not item['check_bit_ok']:
                    status = "CHECKSUM FAIL"
                if item['sync_lost']:
                    status = "RESYNC"
                f.write("[{:10.5f}] {:02x} [{:s}{:s}] [{:s}]\n".format(
                    byte_time, byte_value, ascii[byte_value], cbm_display_codes[byte_value], status))


# Do it right away if we're run as a script
if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',
                        default="/mnt/ganymede4/dcf21/cassette_archive/drawer_br/drawer_br_tape02a_c16_basic1.wav",
                        type=str,
                        dest="input_filename",
                        help="Input WAV file to process")
    parser.add_argument('--output',
                        default="/tmp/computer_tape/",
                        type=str,
                        dest="output_directory",
                        help="Directory in which to put the extracted files")
    parser.add_argument('--debug',
                        action='store_true',
                        dest="debug",
                        help="Show full debugging output")
    parser.set_defaults(debug=False)
    args = parser.parse_args()

    # Set up a logging object
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        stream=sys.stdout,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.debug(__doc__.strip())

    # Open input audio file
    processor = WavCommodoreFileSearch(input_filename=args.input_filename)

    # Search for Commodore files
    chunk_list = processor.search_wav_file()

    # Write a textual summary of the list of the chunks we found
    chunk_description = processor.write_list_of_chunks(chunk_list=chunk_list)
    logging.info(chunk_description)

    # Extract the Commodore files we found to output
    processor.extract_files(chunk_list=chunk_list, output_dir=args.output_directory)
