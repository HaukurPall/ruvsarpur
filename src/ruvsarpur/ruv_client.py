import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, TypedDict

from gql import Client, gql
from gql.client import AsyncClientSession
from gql.transport.aiohttp import AIOHTTPTransport

log = logging.getLogger(__name__)


class Episode(TypedDict):
    id: str
    title: str
    file: str


class Program(TypedDict):
    id: str
    title: str
    foreign_title: str
    short_description: str
    episodes: List[Episode]


Programs = Dict[str, Program]


class RUVClient:
    """An HTTP client to gather a program list from ruv.is."""

    def __init__(self) -> None:
        self.url = "https://www.ruv.is/gql/"
        transport = AIOHTTPTransport(self.url)
        self.client = Client(transport=transport, execute_timeout=30)

    @staticmethod
    async def _query_categories(session: AsyncClientSession) -> List[str]:
        query = gql(
            """
            query getCategorys($station: StationSearch!) {
                Category(station: $station) {
                    categories {
                        title
                        slug
                    }
                }
            }
            """
        )

        params = {
            "station": "tv",
        }
        result = await session.execute(query, variable_values=params)
        category_slugs = [category["slug"] for category in result["Category"]["categories"]]  # type: ignore
        return category_slugs

    @staticmethod
    async def _query_category(session: AsyncClientSession, category: str) -> List[Program]:
        query = gql(
            """
            query getKrakkaRUVCategories($station: StationSearch!, $category: String!) {
                Category(station: $station, category: $category) {
                    categories {
                        programs {
                            short_description
                            episodes {
                                id
                                title
                                file
                            }
                            title
                            foreign_title
                            short_description
                            id
                        }
                    }
                }
            }
            """
        )
        params = {
            "station": "tv",
            "category": category,
        }
        result = await session.execute(query, variable_values=params)
        return [
            program for category in result["Category"]["categories"] for program in category["programs"]  # type: ignore
        ]

    async def _get_all_categories(self) -> List[Program]:
        async with self.client as session:
            categories = await self._query_categories(session)
            list_of_programs_lists = await asyncio.gather(
                *[asyncio.create_task(self._query_category(session, category=category)) for category in categories]
            )
            return [program for program_list in list_of_programs_lists for program in program_list]

    @staticmethod
    async def _query_all_programs(session: AsyncClientSession) -> List[Program]:
        query = gql(
            """
            query {
                Programs {
                    short_description
                    episodes {
                        id
                        title
                        file
                    }
                    title
                    foreign_title
                    short_description
                    id
                }
            }
            """
        )
        result = await session.execute(query)
        return [program for program in result["Programs"]]  # type: ignore

    async def _get_all_programs(self) -> Programs:
        async with self.client as session:
            programs = await self._query_all_programs(session)
            programs_dict = {program["id"]: program for program in programs}
            categories = await self._query_categories(session)
            list_of_programs_lists = await asyncio.gather(
                *[asyncio.create_task(self._query_category(session, category=category)) for category in categories]
            )
            programs_with_extra_info = {
                program["id"]: program for program_list in list_of_programs_lists for program in program_list
            }
            self._add_extra_info(programs_dict, programs_with_extra_info)
            return programs_dict

    def get_all_programs(self) -> Programs:
        return asyncio.run(self._get_all_programs())

    @staticmethod
    def _add_extra_info(programs: Programs, programs_extra_info: Programs) -> None:
        """Adds extra information from another program list to the first one."""
        for p_id, program in programs.items():
            if p_id in programs_extra_info:
                for key in ["short_description", "foreign_title"]:
                    program[key] = programs_extra_info[program["id"]][key]  # type: ignore


def save_programs(file_path: Path, programs: Programs):
    with file_path.open("w") as f:
        json.dump(programs, f)


def load_programs_cache(file_path: Path) -> Programs:
    with file_path.open("r") as f:
        return json.load(f)


def load_programs(force_reload, cache: Path) -> Programs:
    """Load the programs by either loading from cache or by querying ruv.is."""
    if force_reload:
        programs = RUVClient().get_all_programs()
    else:
        try:
            return load_programs_cache(cache)
        except FileNotFoundError:
            programs = RUVClient().get_all_programs()
    save_programs(cache, programs)
    log.info(
        f"Loaded {len(programs)} programs and {sum([len(program['episodes']) for program in programs.values()])} episodes"
    )
    return programs
