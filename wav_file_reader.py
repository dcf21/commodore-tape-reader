#!../../auto/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# wav_file_reader.py
#
# The Python script in this file provides a utility class for extracting files
# from WAV recordings containing the audio of tapes recorded by 8-bit computers.
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
Utility class to read WAV audio streams of old 8-bit computer tapes, and extract a list of zero-crossings or
wave-form peaks from the audio. This list can then be analysed to extract the binary bits encoded on the tape.
"""

import logging
import struct
import wave

from typing import List


class WavFileReader:
    """
    Utility class to read WAV audio streams of old 8-bit computer tapes, and extract a list of zero-crossings or
    wave-form peaks from the audio. This list can then be analysed to extract the binary bits encoded on the tape.
    """

    def __init__(self, input_filename: str):
        """
        Utility class to read WAV audio streams of old 8-bit computer tapes, and extract a list of zero-crossings or
        wave-form peaks from the audio.

        :param input_filename:
            Filename of the wav file to process.
        :return:
        """

        # Input settings
        self.input_filename = input_filename

        # Open wav file
        self.wav_file = wave.open(self.input_filename, "rb")

        # Populate metadata about the input audio stream
        self.channels = self.wav_file.getnchannels()  # channel count
        self.bit_width = self.wav_file.getsampwidth() * 8  # bits per sample
        self.max_amplitude = pow(2, self.bit_width)  # frame value
        self.sampling_frequency = self.wav_file.getframerate()  # Hz
        self.frame_count = self.wav_file.getnframes()  # frame count
        self.length = self.frame_count / self.sampling_frequency  # seconds

        # Calculate the minimum amplitude of a wave before we count it as a wave cycle
        self.min_wave_amplitude_fraction = 0.05
        self.min_wave_amplitude_value = self.min_wave_amplitude_fraction * self.max_amplitude

        # Report metadata about the wav file
        logging.info("Opened <{}>: {} channels, {} bits wide, {} frames/sec, length {:.0f}m{:.1f}s".format(
            self.input_filename, self.channels, self.bit_width, self.sampling_frequency,
            self.length / 60, self.length % 60))

        # Check that wav file is 16-bit mono, the only format we currently support
        assert self.channels == 1, "This script currently only supports 16-bit mono wav files"
        assert self.bit_width == 16, "This script currently only supports 16-bit mono wav files"

    def rewind(self):
        """
        Return to the beginning of the WAV file.

        :return:
            None
        """

        self.wav_file.rewind()

    def fetch_wav_file_sample(self, invert_wave: bool = False):
        """
        Fetch a single sample from a 16-bit mono WAV file.

        :param invert_wave:
            Boolean indicating whether we invert the waveform.
        :return:
            A 16-bit signed integer value
        """

        # Fetch a single frame from the wav file
        wave_data = self.wav_file.readframes(1)
        if len(wave_data) == 0:
            return None

        # Extract value (assumes 16-bit mono)
        frame_value = int(struct.unpack("<h", wave_data)[0])

        # Invert wave if requested
        if invert_wave:
            frame_value *= -1

        # Return 16-bit signed integer
        return frame_value

    def fetch_zero_crossing_times(self, invert_wave: bool = False):
        """
        Extract a list of all the times when the signal on the tape crosses zero, in the downward direction. We only
        count crossings when the wave amplitude exceeds <self.min_wave_amplitude_value> to avoid detecting many
        spurious zero-crossings in silent sections of the audio.

        :param invert_wave:
            Boolean indicating whether we invert the waveform before searching for descending zero-crossings (meaning
            that we actually look for ascending crossings).
        :return:
            List[float] of times of zero-crossings, in seconds
        """

        # Start from the beginning of the file
        self.rewind()

        file_position = 0  # Current file position - sample number
        zero_crossing_times: List[float] = []  # Output list of zero-crossing times
        seen_adequate_amplitude = False  # Flag indicating whether the wave amplitude is greater than minimum allowed
        was_above_zero = False  # Flag indicating whether previous audio sample was greater than zero

        # Cycle through file, sample by sample, looking for downward zero crossings
        while True:
            # Fetch a single frame from the wav file
            frame_value = self.fetch_wav_file_sample(invert_wave=invert_wave)

            # Check for end of audio stream
            if frame_value is None:
                break

            # Process sample - to avoid jitter, we only count zero-crossings where the wave has been an adequate
            # distance above zero
            if frame_value > self.min_wave_amplitude_value:
                seen_adequate_amplitude = True

            # Downward zero crossing?
            if frame_value < 0 and was_above_zero and seen_adequate_amplitude:
                # Record time of this event, in seconds
                zero_crossing_times.append(file_position / self.sampling_frequency)
                seen_adequate_amplitude = False

            # Update flags, and advance to next audio sample
            was_above_zero = frame_value >= 0
            file_position += 1

        # Log number of zero-crossings
        logging.debug("Found {:d} zero-crossing events".format(len(zero_crossing_times)))

        # Return list of time points in wav file where wave crosses zero
        return zero_crossing_times

    def fetch_wave_peak_times(self, bracket_window: int, invert_wave: bool = False):
        """
        Extract a list of all the times when the signal on the tape passes a maximum.

        :param bracket_window:
            To qualify, all wave peaks must be higher than all neighbouring points in a window of this width, centered
            on the peak (width counted in samples).
        :param invert_wave:
            Boolean indicating whether we invert the waveform before searching for peaks (meaning that we actually
            look for troughs).
        :return:
            List[float] of times of wave peaks, in seconds
        """

        # Start from the beginning of the file
        self.rewind()

        # Check that bracket window is an adequately-sized integer
        bracket_window = int(bracket_window)
        assert bracket_window > 10, "Unreasonably short bracket_window."
        buffer_middle = int(bracket_window / 2)

        # Start building list of wave peak times
        file_position = 0  # Current file position - sample number
        peak_times: List[float] = []  # Output list of wave-peak times
        buffer = []  # Rolling buffer of length <bracket>, used to check peak is highest in neighbourhood

        # Cycle through file looking for wave peaks
        while True:
            # Fetch a single frame from the wav file
            frame_value = self.fetch_wav_file_sample(invert_wave=invert_wave)

            # Check for end of audio stream
            if frame_value is None:
                break

            # Add this sample to processing buffer
            buffer.append(frame_value)

            # Only proceed if the buffer has been filled
            if len(buffer) > bracket_window:
                # Keep the buffer the same length
                buffer.pop(0)

                # Check whether the sample in the middle of the buffer is the highest in the whole buffer.
                # For efficiency, this <if> statement is written so the first few items quickly exclude most
                # datapoints. The later parts of the <if> statement are much slower to compute!
                if (
                        (buffer[buffer_middle] > buffer[buffer_middle - 1]) and
                        (buffer[buffer_middle] >= buffer[buffer_middle + 1]) and
                        (buffer[buffer_middle] > buffer[0]) and
                        (buffer[buffer_middle] > buffer[bracket_window - 1]) and
                        (buffer[buffer_middle] == max(buffer)) and
                        (buffer[buffer_middle] > min(buffer) + self.min_wave_amplitude_value)
                ):
                    # We have found a wave-peak, so log its time
                    peak_times.append(file_position / self.sampling_frequency)

            # Advance to the next audio sample
            file_position += 1

        # Log number of zero-crossings
        logging.debug("Found {:d} wave-peak events".format(len(peak_times)))

        # Return list of time points in wav file where there is a peak
        return peak_times

    @staticmethod
    def fetch_pulse_list(input_events: List):
        """
        Extract a list of the intervals (in seconds) representing a single wave cycle. We call these intervals
        'pulses', in common with the literature on the Commodore tape format (though we also use the same method
        to extract data from Acorn computer tapes). The wave cycles are bounded by either zero-crossings, or wave
        peaks, depending which phase of the waveform we treat as the start point.

        :param input_events:
            A list of the input times when new wave cycles start. These input times may represent zero-crossings,
            or wave maxima / minima.
        :return:
            A list of dictionaries describing the intervals, called pulses, in which there is a single wave cycle
        """

        pulse_list = []  # List of all the pulses (wave cycles) we found

        # Loop through all of the input events which signify the start of a new wave cycle
        for i in range(1, len(input_events)):
            # Calculate the time elapsed since the start of the previous wave cycle
            pulse_length = input_events[i] - input_events[i - 1]

            # Add a descriptor for this cycle
            pulse_list.append({
                'time': input_events[i - 1],  # The time of the start of this wave cycle on the tape
                'length_sec': pulse_length  # The duration of this wave cycle, in seconds
            })

        # Return pulse (wave cycle) list
        return pulse_list

    def time_string(self, file_position=None):
        """
        Return a human-readable string representation of a time point in the audio stream.

        :param file_position:
            Optionally, specify the file position to display a timestamp for. By default, show the current position.
        :return:
            str
        """

        # If no file position was specified, determine the current position in the audio file
        if file_position is None:
            file_position = self.wav_file.tell()

        # Convert file position (sample number) into a time-point measured in seconds
        file_time = file_position / self.sampling_frequency

        # Return a human-readable timestamp
        return "[{:10.5f}]".format(file_time)
