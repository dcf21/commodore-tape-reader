# commodore_tape_parse.py

This Python script extracts binary files from WAV recordings of audio cassette tapes recorded by 8-bit Commodore computers (e.g. C64, C16, Plus/4 and C128). These will typically have been recorded using a Commodore 1530 / C2N / 1531 datasette.

This script was used by the author to recover all the Commodore tapes archived on the website <https://files.dcford.org.uk/>.

This script has been tested on files saved by Commodore 16, 64 and 128 computers. It automatically determines the clock speed used to encode the pulses found on the tape, based on the pulse intervals found, and so can tolerate recordings whose playback speed is significantly wrong.

By default, this script simply exports all the files to a specified output directory. If a more sophisticated export is required, it is simple to call the <WavCommodoreFileSearch> class from an external script to perform other actions on the files found.

## Limitations

* This script only reads files saved by the Commodore KERNAL, not turbo loading tapes (i.e. it will not read most commercial releases, but it will read most tapes you may have recorded yourself).

* This script only accepts 16-bit mono wav files as input. Any bit rate is supported, but >= 44.1kHz is recommended.

* This script is quite sensitive to low-frequency noise. You may be able to recover more files if you use audio-editing software (e.g. Adobe Audition or Audacity) to pass the input audio through a ~100-Hz high-pass filter before calling this script.

## Command-line syntax

### Usage:

./commodore_tape_parse.py [-h] [--input INPUT_FILENAME] [--output OUTPUT] [--debug]

### Options:

|Switch                         |Meaning                                                                              |
|-------------------------------|-------------------------------------------------------------------------------------|
|-h, --help                     |show this help message and exit                                                      |
|--input INPUT                  |Input WAV file to process                                                            |
|--output OUTPUT                |Directory in which to put the extracted files                                        |
|--debug                        |Show full debugging output                                                           |


## License

This code is distributed under the Gnu General Public License V3. It is (C) Dominic Ford 2022.

## Author

Dominic Ford - <https://dcford.org.uk/>
