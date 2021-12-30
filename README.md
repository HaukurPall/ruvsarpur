# RÚV Sarpur improved

This is a fork of https://github.com/sverrirs/ruvsarpur [Project website](https://sverrirs.github.io/ruvsarpur/)

# Installation

Be sure to have these things installed

- Python version 3.8
- [ffmpeg](https://www.ffmpeg.org/download.html)

```
pip install git+https://github.com/HaukurPall/ruvsarpur
```

# Usage

This program is not as fully featured as the original ruvsarpur but it has these benefits:

- Faster (really fast) downloading of the available programs on ruv.is
- More available programs (yes, really).
- Simple terminal client; `ruvsarpur`.

## Finding and listing shows

```
ruvsarpur --work-dir $PWD search "hvolpa" "sámur" "skotti" "lestrarhvutti" "úmísúmí" "kúlu" "klingjur" "teitur" "blæja" "hrúturinn" --ignore-case
# prints
| Program title                   | Foreign title             |   Episode count |   Program ID | Short description                        |
|---------------------------------|---------------------------|-----------------|--------------|------------------------------------------|
| Hvolpasveitin                   | Paw Patrol VII            |               5 |        31660 | Hvolparnir síkátu halda áfram ævintýrum  |
| Hvolpasveitin                   | Paw Patrol VI             |               8 |        31659 | Sjötta serían af Hvolpsveitinni þar sem  |
| Hæ Sámur                        | Hey Duggee                |               6 |        30699 | Vinalegi hundurinn Sámur hvetur börn til |
| Skotti og Fló                   | Munki and Trunk           |              12 |        30275 | Apinn Skotti og fíllinn Fló eru bestu vi |
| Lestrarhvutti                   | Dog Loves Books           |               2 |        29782 | Hvutti og Kubbur dýrka bækur og á bókasa |
| Úmísúmí                         | Team Umizoomi I           |               1 |        30265 | Stærðfræðiofurhetjurnar Millý, Geó og Bó |
| Kúlugúbbarnir                   | Bubble Guppies III        |               4 |        30227 | Krúttlegir teiknimyndaþættir um litla ha |
| Teitur í jólaskapi              | Timmy: Christmas Surprise |               1 |        32517 | Það er aðfangadagur í leikskólanum hjá T |
| Blæja                           | Bluey                     |              12 |        31684 | Blæja er sex ára hundur sem er stútfull  |
| Hrúturinn Hreinn: Björgun Teits |                           |               1 |        32509 | Hreinn og vinir hans leggjast í leiðangu |
```

## Downloading shows

To download shows you supply the `download-program` command a list of program ids to download.

The easiest way to do this is to append `--only-ids` to the search command and pipe it to the `download-program` command:

```
ruvsarpur --work-dir $PWD search "hvolpa" "sámur" "skotti" "lestrarhvutti" "úmísúmí" "kúlu" "klingjur" "teitur" "blæja" "hrúturinn" --ignore-case --only-ids | ruvsarpur --work-dir $PWD download-program
```

### Keeping track of downloaded shows

The script keeps track of the shows that have already been downloaded so that you do not download them again.

TODO: Explain how.

### Choosing video quality

The script automatically attempts to download videos using the highest video quality for all download streams, this is equivilent of Full-HD resolution or 3600kbps.

TODO: Explain other options
