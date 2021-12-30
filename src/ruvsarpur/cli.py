import logging
from pathlib import Path
from typing import Optional, Tuple

import click
from tabulate import tabulate

from ruvsarpur.ruv_client import load_programs
from ruvsarpur.search import get_all_programs_by_pattern, program_results

DEFAULT_WORK_DIR = Path.home() / "ruvsarpur"
WORK_DIR = DEFAULT_WORK_DIR
PROGRAMS_JSON = "programs.json"
DOWNLOAD_DIR_NAME = "downloads"


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
    logging.basicConfig(level=log_level)
    # Increase the log level of gql - otherwise we are spammed
    logging.getLogger("gql").setLevel(logging.WARN)
    global WORK_DIR
    WORK_DIR = work_dir
    if not WORK_DIR.exists():
        WORK_DIR.mkdir(parents=True, exist_ok=True)


@main.command()
@click.argument("patterns", type=str, nargs=-1)
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
    found_programs = []
    for pattern in patterns:
        found_programs.extend(get_all_programs_by_pattern(programs, pattern, ignore_case))
    if only_ids:
        click.echo(" ".join([program["id"] for program in found_programs]))
    else:
        headers, rows = program_results(found_programs)
        click.echo(tabulate(tabular_data=rows, headers=headers, tablefmt="github"))


@main.command()
@click.argument("program-ids", nargs=-1, type=str)
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
def download_program(program_ids, quality: Optional[int]):
    """Download the supplied program ids. Can be multiple.
    Use the 'search' functionality with --only-ids to get them.
    You can then pipe them to this command programatically."""
    pass


if __name__ == "__main__":
    main()
