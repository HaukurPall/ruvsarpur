"""A module for searching for programs."""
import logging
from typing import List, Tuple

from ruvsarpur.ruv_client import Program

log = logging.getLogger(__name__)


def get_all_programs_by_pattern(programs: List[Program], pattern: str, ignore_case: bool) -> List[Program]:
    """Get all programs that match the pattern.
    Can be multiple.
    """
    if ignore_case:
        pattern = pattern.lower()
    found_programs = []
    for program in programs:
        foreign_title = program.get("foreign_title", None)
        title = program.get("title", "")
        if ignore_case:
            foreign_title = foreign_title.lower() if foreign_title else None
            title = title.lower()
        if pattern in title or (foreign_title is not None and pattern in foreign_title):
            found_programs.append(program)
    return found_programs


ProgramRow = Tuple[str, str, int, str]
ProgramHeader = Tuple[str, str, str, str]


def program_results(programs: List[Program]) -> Tuple[ProgramHeader, List[ProgramRow]]:
    """Format the program results for printing."""
    header = ("Program title", "Foreign title", "Episode count", "Program ID")
    rows = []
    for program in programs:
        try:
            rows.append((program["title"], program["foreign_title"], len(program["episodes"]), program["id"]))
        except KeyError:
            log.warn("Malformed program: %s", program)
        except AttributeError:
            log.warn("Malformed program: %s", program)
    return header, rows
