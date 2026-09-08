"""
What the register does once, when the service starts, before the first request reaches an endpoint.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from skyscanner_common.logging_utils import get_logger
from skyscanner_common.mongo import MongoProvider

from truth_service.repositories.assumption_repository import AssumptionRepository
from truth_service.repositories.industry_repository import IndustryRepository
from truth_service.repositories.schema_repository import SchemaRepository

# ----- CONSTS ----- #

LOGGER = get_logger(__name__)

# ----- FUNCTIONS ----- #


async def prepare_database(provider: MongoProvider) -> None:
    """
    Declare every index the register is read through, so that a fresh database answers as quickly as an old one.

    Nothing is seeded. The register comes up empty and stays that way until somebody writes into it.

    :param provider: Owner of the shared motor client.
    """
    for repository in (
        IndustryRepository(provider=provider),
        SchemaRepository(provider=provider),
        AssumptionRepository(provider=provider),
    ):
        await repository.ensure_indexes()

    LOGGER.info("The register is indexed and ready")
