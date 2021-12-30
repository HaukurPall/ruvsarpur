import logging
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

import click
import ffpb
from tabulate import tabulate
from tqdm import tqdm

from ruvsarpur.hls_downloader import create_ffmpeg_download_command, load_m3u8_available_resolutions
from ruvsarpur.ruv_client import Programs, load_programs
from ruvsarpur.search import get_all_programs_by_pattern, program_results

DEFAULT_WORK_DIR = Path.home() / "ruvsarpur"
WORK_DIR = DEFAULT_WORK_DIR
PROGRAMS_JSON = "programs.json"
DOWNLOAD_DIR_NAME = "downloads"
PREVRECORDED_LOG = "prevrecorded.log"
log = logging.getLogger(__name__)


@click.group()
@click.option(
    "--work-dir",
    help="""The working directory of the program.
For example downloaded content is placed in the folder "$WORK_DIR/downloads".
The program list is cached as "$WORK_DIR/programs.json".
The downloaded episode list is stored in "$WORK_DIR/downloaded_episodes.txt".
""",
    default=DEFAULT_WORK_DIR,
    type=Path,
)
@click.option("--log-level", default="INFO", help="The log level of the stdout.")
def main(work_dir: Path, log_level):
    logging.basicConfig(level=log_level, format="%(asctime)s: %(message)s")
    # Increase the log level of gql - otherwise we are spammed
    logging.getLogger("gql").setLevel(logging.WARN)
    global WORK_DIR
    WORK_DIR = work_dir
    if not WORK_DIR.exists():
        WORK_DIR.mkdir(parents=True, exist_ok=True)


@main.command()
@click.argument("patterns", type=str, nargs=-1, required=True)
@click.option("--ignore-case/--no-ignore-case", default=False, help="Should we ignore casing when searching?")
@click.option("--only-ids/--no-only-ids", default=False, help="Should we only return the found program ids?")
@click.option(
    "--force-reload-programs/--no-force-reload-programs",
    default=False,
    help="Should we force reloading the program list?",
)
def search(patterns: Tuple[str, ...], ignore_case: bool, only_ids: bool, force_reload_programs: bool):
    """Search for a program based on the patterns provided.
    Make sure that each pattern is separated by a space by surrounding each pattern with quotation marks:
    "pattern one" "pattern two"."""
    # TODO: Add support for checking date of last programs fetch.
    programs = load_programs(force_reload=force_reload_programs, cache=WORK_DIR / PROGRAMS_JSON)
    found_programs: Programs = {}
    for pattern in patterns:
        found_programs.update(get_all_programs_by_pattern(programs, pattern, ignore_case))
    if only_ids:
        click.echo(" ".join([str(id) for id in found_programs]))
    else:
        headers, rows = program_results(found_programs)
        click.echo(tabulate(tabular_data=rows, headers=headers, tablefmt="github"))


def maybe_read_stdin(ctx, param, value):
    if not value and not click.get_text_stream("stdin").isatty():
        return click.get_text_stream("stdin").read().strip()
    else:
        return value


@main.command()
@click.argument("program-ids", nargs=-1, type=str, callback=maybe_read_stdin)
@click.option(
    "--quality",
    help="""The quality of the file to download.
The default value, when not supplied, is the highest quality.
Usually ranges from 0-4, where 0 is the worst quality (~426x240) and 4 is the best ~1920x1080 = Full HD or 1080p.
3 tends to be 1280x720 = HD or 720p.
""",
    type=int,
    default=None,
)
@click.option(
    "--force-reload-programs/--no-force-reload-programs",
    default=False,
    help="Should we force reloading the program list?",
)
def download_program(program_ids, quality: Optional[int], force_reload_programs):
    """Download the supplied program ids. Can be multiple.
    Use the 'search' functionality with --only-ids to get them and pipe them to this command."""
    program_id_list: List[str] = program_ids.strip().split(" ")
    programs = load_programs(force_reload=force_reload_programs, cache=WORK_DIR / PROGRAMS_JSON)
    selected_episodes = {
        episode["id"]: {
            "p_title": programs[program_id]["title"],
            "title": episode["title"],
            "foreign_title": programs[program_id]["foreign_title"],
            "file": episode["file"],
            "id": episode["id"],
        }
        for program_id in program_id_list
        for episode in programs[program_id]["episodes"]
    }
    downloaded_episodes = read_downloaded_episodes(WORK_DIR / PREVRECORDED_LOG)
    episodes_to_download = {id: episode for id, episode in selected_episodes.items() if id not in downloaded_episodes}
    log.info(f"Will download {len(episodes_to_download)} episodes")
    for id, episode in tqdm(episodes_to_download.items()):
        episode_name = f"{episode['p_title']} - {episode['title']} - {episode['foreign_title']}"
        log.info(f"Working on {episode_name}")
        resolutions = load_m3u8_available_resolutions(episode["file"])
        log.info(f"Available resolutions: {resolutions_to_str(resolutions)}")
        if quality is None:
            quality = len(resolutions) - 1
        log.info(f"You selected quality={quality}:{'x'.join([str(x) for x in resolutions[quality]])}")
        log.info(f"Downloading")
        output_file = WORK_DIR / DOWNLOAD_DIR_NAME / f"{episode_name}.mp4"
        ffmpeg_command = create_ffmpeg_download_command(episode["file"], quality, output_file=output_file)
        ffpb.main(argv=ffmpeg_command, stream=sys.stderr, encoding="utf-8", tqdm=tqdm)
        if output_file.exists():
            append_downloaded_episode(WORK_DIR / PREVRECORDED_LOG, id)


def resolutions_to_str(resolutions: List[Tuple[int, int]]) -> str:
    resolutions_as_str = ["x".join(str(x) for x in resolution) for resolution in resolutions]
    resolutions_str = []
    for idx, resolution_str in enumerate(resolutions_as_str):
        resolutions_str.append(f"{idx}:{resolution_str}")
    return " ".join(resolutions_str)


def read_downloaded_episodes(path: Path) -> Set[str]:
    downloaded_episodes = set()
    if path.exists():
        with path.open() as f:
            for line in f:
                downloaded_episodes.add(line.strip())
    return downloaded_episodes


def append_downloaded_episode(path: Path, episode_id: str):
    with path.open("a") as f:
        f.write(f"{episode_id}\n")


if __name__ == "__main__":
    main()
