# commodore_tape_parse.py

This Python script extracts binary files from WAV recordings of audio cassette tapes recorded by 8-bit Commodore computers (e.g. C64, C16, Plus/4 and C128). These will typically have been recorded using a Commodore 1530 / C2N / 1531 datasette. It can return the files either in raw form, or as a TAP file for use in Commodore emulators such as VICE.

This script was used by the author to recover all the Commodore tapes archived on the website <https://files.dcford.org.uk/>.

This script has been tested on files saved by Commodore 16, 64 and 128 computers. It automatically determines the clock speed used to encode the pulses found on the tape, based on the pulse intervals found, and so can tolerate recordings whose playback speed is significantly wrong.

By default, this script simply exports all the files to a specified output directory. If a more sophisticated export is required, it is simple to call the <WavCommodoreFileSearch> class from an external script to perform other actions on the files found.

## Usage

* This script can convert any tape into TAP format for use in an emulator such as VICE. However, the functions to extract the raw contents of files will only recover files saved by theCommodore KERNAL, not turbo loading tapes (i.e. it cannot extract the contents of most commercial releases, though you can load them into an emulator as a TAP file).

* Any bit rate is supported, but >= 44.1kHz is recommended. Both mono and stereo recordings are accepted, but stereo is recommended, and the best channel will automatically be selected -- very often one channel is (much) less noisy than the other.

* This script is quite sensitive to low-frequency noise. You may be able to recover more files if you use audio-editing software (e.g. Adobe Audition or Audacity) to pass the input audio through a ~100-Hz high-pass filter before calling this script.

## Command-line syntax

./commodore_tape_parse.py [-h] [--input INPUT_FILENAME] [--output OUTPUT_DIR] [--tap FILENAME] [--debug]

### Options:

| Switch                 | Meaning                                                                |
|------------------------|------------------------------------------------------------------------|
| -h, --help             | Show help message and exit                                             |
| --input INPUT_FILENAME | Input WAV file to process                                              |
| --output OUTPUT_DIR    | Directory in which to put the extracted files                          |
| --tap FILENAME         | Filename for output TAP tape image (for use in emulators such as Vice) |
| --debug                | Show full debugging output                                             |


## License

This code is distributed under the Gnu General Public License V3. It is (C) Dominic Ford 2022.

## Author

Dominic Ford - <https://dcford.org.uk/>
