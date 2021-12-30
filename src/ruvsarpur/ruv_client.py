import asyncio
import json
from pathlib import Path
from typing import List, TypedDict

import m3u8
from gql import Client, gql
from gql.client import AsyncClientSession
from gql.transport.aiohttp import AIOHTTPTransport


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


class RUVClient:
    """An HTTP client to gather a program list from ruv.is."""

    def __init__(self) -> None:
        self.url = "https://www.ruv.is/gql/"
        transport = AIOHTTPTransport(
            self.url,
            headers={
                "Referer": "https://www.ruv.is/sjonvarp",
                "Origin": "https://www.ruv.is",
            },
        )
        self.client = Client(transport=transport, execute_timeout=30)

    @staticmethod
    async def _get_categories(session: AsyncClientSession) -> List[str]:
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
    async def _get_category(session: AsyncClientSession, category: str) -> List[Program]:
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
            categories = await self._get_categories(session)
            list_of_programs_lists = await asyncio.gather(
                *[asyncio.create_task(self._get_category(session, category=category)) for category in categories]
            )
            return [program for program_list in list_of_programs_lists for program in program_list]

    def get_all_programs(self) -> List[Program]:
        return asyncio.run(self._get_all_categories())


def save_programs(file_path: Path, programs: List[Program]):
    with file_path.open("w") as f:
        json.dump(programs, f)


def load_programs_cache(file_path: Path) -> List[Program]:
    with file_path.open("r") as f:
        return json.load(f)


def load_programs(force_reload, cache: Path) -> List[Program]:
    """Load the programs by either loading from cache or by querying ruv.is."""
    if force_reload:
        programs = RUVClient().get_all_programs()
    else:
        try:
            return load_programs_cache(cache)
        except FileNotFoundError:
            programs = RUVClient().get_all_programs()
    save_programs(cache, programs)
    return programs
