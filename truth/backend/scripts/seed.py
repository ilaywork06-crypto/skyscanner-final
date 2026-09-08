"""
Fill the register with a stated amount of assumptions, for seeing how it behaves at a size worth testing.

    uv run python truth/backend/scripts/seed.py --count 100000

The industries and the schemas are written once and reused, and the assumptions are written in batches: a
hundred thousand documents one round trip at a time is a hundred thousand round trips, which says nothing
about the register and takes a quarter of an hour to say it.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

import argparse
import asyncio
import random
import sys
import time
from datetime import timedelta

from skyscanner_common.datetime_utils import utc_now
from skyscanner_common.ids import new_id
from skyscanner_common.mongo import MongoProvider

from truth_service.bootstrap import prepare_database
from truth_service.documents import (
    AssumptionDocument,
    IndustryDocument,
    SchemaDocument,
    StoredScheme,
    build_search_text,
)
from truth_service.models.common import IndustryReference, SchemaReference
from truth_service.repositories.assumption_repository import AssumptionRepository
from truth_service.repositories.industry_repository import IndustryRepository
from truth_service.repositories.schema_repository import SchemaRepository
from truth_service.settings import get_truth_mongo_settings

# ----- CONSTS ----- #

BATCH_SIZE: int = 2000

INDUSTRY_NAMES: tuple[str, ...] = ("Telemetry", "Aviation", "Maritime", "Energy", "Logistics")
PARTIES: tuple[str, ...] = ("Engineering", "Operations", "Finance", "Safety", "Programme")
CREATORS: tuple[str, ...] = ("dana", "yossi", "noa", "amit", "script")
TAGS: tuple[str, ...] = ("baseline", "contested", "carried over", "provisional", "validated", "at risk")
CONFIDENCE: tuple[str, ...] = ("High", "Medium", "Low")
SENSOR_CLASSES: tuple[str, ...] = ("A", "B", "C")

SCHEMES: tuple[tuple[str, str, list[dict[str, object]]], ...] = (
    (
        "Flight Performance",
        "Attributes of a flight performance assumption.",
        [
            {"key": "cruise_speed", "display_name": "Cruise speed", "type": "confined_float",
             "required": True, "array": False, "min": 0, "max": 900},
            {"key": "cruise_altitude", "display_name": "Cruise altitude", "type": "confined_number",
             "required": False, "array": False, "min": 0, "max": 60000},
            {"key": "fuel_burn", "display_name": "Fuel burn", "type": "confined_float",
             "required": False, "array": False},
            {"key": "confidence", "display_name": "Confidence", "type": "enum",
             "required": True, "array": False, "options": list(CONFIDENCE)},
            {"key": "verified", "display_name": "Verified", "type": "boolean", "required": False, "array": False},
            {"key": "sources", "display_name": "Sources", "type": "string", "required": False, "array": True},
        ],
    ),
    (
        "Sensor Baseline",
        "What a telemetry sensor is assumed to report.",
        [
            {"key": "sample_rate", "display_name": "Sample rate", "type": "confined_float",
             "required": True, "array": False, "min": 0},
            {"key": "drift", "display_name": "Drift", "type": "confined_float", "required": False, "array": False},
            {"key": "sensor_class", "display_name": "Sensor class", "type": "enum",
             "required": False, "array": False, "options": list(SENSOR_CLASSES)},
            {"key": "commissioned", "display_name": "Commissioned", "type": "date",
             "required": False, "array": False},
        ],
    ),
    (
        "Port Throughput",
        "",
        [{"berth_count": "int"}, {"tonnes_per_day": "float"}, {"operator": "string"}],
    ),
)

# ----- FUNCTIONS ----- #


async def ensure_industries(repository: IndustryRepository) -> list[IndustryReference]:
    """
    Write the industries if they are not there yet, and hand back what to file assumptions under.

    :param repository: Reads and writes of the industries.
    :return: Every industry of the register, as an assumption names one.
    """
    references: list[IndustryReference] = []
    for name in INDUSTRY_NAMES:
        existing = await repository.find_by_name(name)
        if existing is None:
            existing = await repository.insert(
                IndustryDocument(name=name, description=f"{name} assumptions", creator="seed"),
            )
        references.append(IndustryReference(id=existing.id, name=existing.name))

    return references


async def ensure_schemas(
    repository: SchemaRepository,
    industries: list[IndustryReference],
) -> list[SchemaDocument]:
    """
    Write the declarations if they are not there yet, and hand back the current revision of each.

    :param repository: Reads and writes of the declarations.
    :param industries: Industries the declarations are filed under.
    :return: The current revision of every declaration of the register.
    """
    written: list[SchemaDocument] = []
    for position, (name, description, fields) in enumerate(SCHEMES):
        existing = await repository.find_latest_by_name(name)
        if existing is None:
            lineage = new_id()
            existing = await repository.insert(
                SchemaDocument(
                    id=lineage,
                    lineage=lineage,
                    name=name,
                    description=description,
                    scheme=StoredScheme(fields=fields),  # type: ignore[arg-type]
                    creator="seed",
                    industries=[industries[position % len(industries)]],
                ),
            )
        written.append(existing)

    return written


def build_values(schema: SchemaDocument, index: int, generator: random.Random) -> dict[str, object]:
    """
    Make up what one assumption carries, in the shape the declaration it names asks for.

    The choices are drawn rather than derived from the running number. Deriving them looked fine and was
    not: the declaration is picked by the number as well, so every assumption of one schema ended up with
    the same choice in every enumerated attribute, and a register seeded that way makes every filter and
    every count look like it works when none of them has been tried against more than one value.

    :param schema: Declaration the assumption is written against.
    :param index: Running number of the assumption, which the made up figures vary with.
    :param generator: Source of the choices, seeded so that two runs make the same register.
    :return: The values the assumption carries.
    """
    if schema.name == "Flight Performance":
        return {
            "cruise_speed": 380 + (index % 200),
            "cruise_altitude": 28000 + (index % 12) * 1000,
            "fuel_burn": round(1800 + (index % 700) * 0.5, 2),
            "confidence": generator.choice(CONFIDENCE),
            "verified": generator.choice((True, False)),
            "sources": [f"report-{index % 97}", "flight-manual"],
        }

    if schema.name == "Sensor Baseline":
        return {
            "sample_rate": 20 + (index % 180),
            "drift": round((index % 50) * 0.004, 4),
            "sensor_class": generator.choice(SENSOR_CLASSES),
            "commissioned": (utc_now() - timedelta(days=index % 3000)).date().isoformat(),
        }

    return {
        "berth_count": 2 + (index % 18),
        "tonnes_per_day": round(4000 + (index % 900) * 1.5, 1),
        "operator": f"Operator {index % 40}",
    }


def build_assumption(
    index: int,
    schema: SchemaDocument,
    industries: list[IndustryReference],
    generator: random.Random,
) -> AssumptionDocument:
    """
    Make up one assumption, filed under one or two industries and written against one declaration.

    :param index: Running number of the assumption.
    :param schema: Declaration the assumption is written against.
    :param industries: Every industry of the register.
    :param generator: Source of the choices, seeded so that two runs make the same register.
    :return: The assumption, ready to be written.
    """
    lineage = new_id()
    chosen = generator.sample(industries, k=generator.choice((1, 1, 2)))
    document = AssumptionDocument(
        id=lineage,
        lineage=lineage,
        name=f"{schema.name} assumption {index}",
        assumption_text=(
            f"The {schema.name.lower()} of unit {index % 500} is assumed to hold "
            f"for the {generator.choice(('first', 'second', 'third', 'fourth'))} phase of the programme."
        ),
        proposing_party=generator.choice(PARTIES),
        tags=generator.sample(TAGS, k=generator.choice((1, 2))),
        validation_responsible_parties=generator.sample(PARTIES, k=generator.choice((1, 2))),
        creator=generator.choice(CREATORS),
        created_at=utc_now() - timedelta(minutes=index),
        schemas=[SchemaReference(id=schema.lineage, name=schema.name, revision=schema.revision)],
        industries=chosen,
        values=build_values(schema=schema, index=index, generator=generator),  # type: ignore[arg-type]
    )
    document.search_text = build_search_text(document)

    return document


async def seed(count: int, batch_size: int) -> None:
    """
    Write the whole register and say how long it took.

    :param count: How many assumptions are written.
    :param batch_size: How many assumptions are written per round trip.
    """
    provider = MongoProvider(settings=get_truth_mongo_settings())
    await provider.connect()
    await prepare_database(provider=provider)

    industries = await ensure_industries(IndustryRepository(provider=provider))
    schemas = await ensure_schemas(SchemaRepository(provider=provider), industries=industries)
    assumptions = AssumptionRepository(provider=provider)

    generator = random.Random(20260908)
    started = time.monotonic()
    written = 0

    while written < count:
        batch = [
            build_assumption(
                index=written + position,
                schema=schemas[(written + position) % len(schemas)],
                industries=industries,
                generator=generator,
            )
            for position in range(min(batch_size, count - written))
        ]
        written += await assumptions.insert_many(batch)
        print(f"  {written:>8} / {count} written", end="\r", flush=True)

    elapsed = time.monotonic() - started
    print(f"\nWrote {written} assumptions in {elapsed:.1f}s ({written / max(elapsed, 0.001):.0f}/s)")

    await provider.close()


def main() -> int:
    """
    Read what was asked for and fill the register with it.

    :return: The exit code of the run.
    """
    parser = argparse.ArgumentParser(description="Fill the Truth register with made up assumptions")
    parser.add_argument("--count", type=int, default=1000, help="How many assumptions to write")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="How many to write per round trip")
    arguments = parser.parse_args()

    asyncio.run(seed(count=arguments.count, batch_size=arguments.batch_size))

    return 0


if __name__ == "__main__":
    sys.exit(main())
