"""A module for handling HLS downloading"""

from pathlib import Path
from typing import List, Tuple

import m3u8


def load_m3u8_available_resolutions(url: str) -> List[Tuple[int, int]]:
    """Load the m3u8 file and return the available resolutions after checking for assumptions."""
    m3u8_obj = m3u8.load(url)
    if m3u8_obj.is_variant:
        resolutions = [playlist.stream_info.resolution for playlist in m3u8_obj.playlists]
        assert resolutions == sorted(
            resolutions
        ), f"The resolutions are not sorted in {url}, they need to be \
so we can select the correct stream. Please post this error so it can be handled"
        return resolutions

    raise ValueError(
        f"Unable to figure out available resolutions for url={url}.\nPlease post this error so it can be handled."
    )


def create_ffmpeg_download_command(url: str, stream_num: int, output_file: Path):
    """Create the ffmpeg command required to download a specific stream from a m3u8 playlist."""
    return [
        # fmt: off
        "-i", url,
        "-map", f"0:v:{stream_num}", # First input file, select stream_num from video streams
        "-map", f"0:a:{stream_num}", # Same for audio
        "-codec", "copy" # No re-encoding
        # TODO: Test if this works and whether at all the some subtitles are ever sent.
        "-codec:s", "srt", # Except for subtitles due to some caveats in ffmpeg subtitle handling.
        str(output_file)
        # fmt: on
    ]
