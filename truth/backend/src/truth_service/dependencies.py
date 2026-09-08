"""
The dependency wiring of the register, building the repositories and the services one request needs.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from typing import Annotated, cast

from fastapi import Depends, Request

from skyscanner_common.mongo import MongoProvider

from truth_service.repositories.assumption_repository import AssumptionRepository
from truth_service.repositories.industry_repository import IndustryRepository
from truth_service.repositories.schema_repository import SchemaRepository
from truth_service.services.assumption_service import AssumptionService
from truth_service.services.industry_service import IndustryService
from truth_service.services.schema_service import SchemaService

# ----- FUNCTIONS ----- #


def get_mongo_provider(request: Request) -> MongoProvider:
    """
    Fetch the shared document store provider that was opened when the service started.

    :param request: Incoming request carrying the application state.
    :return: The shared document store provider.
    """
    return cast(MongoProvider, request.app.state.mongo)


def get_industry_service(provider: Annotated[MongoProvider, Depends(get_mongo_provider)]) -> IndustryService:
    """
    Build the service owning the industries.

    :param provider: Owner of the shared motor client.
    :return: The service owning the industries.
    """
    return IndustryService(industries=IndustryRepository(provider=provider))


def get_schema_service(provider: Annotated[MongoProvider, Depends(get_mongo_provider)]) -> SchemaService:
    """
    Build the service owning the declarations.

    :param provider: Owner of the shared motor client.
    :return: The service owning the declarations.
    """
    return SchemaService(
        schemas=SchemaRepository(provider=provider),
        industries=IndustryRepository(provider=provider),
    )


def get_assumption_service(provider: Annotated[MongoProvider, Depends(get_mongo_provider)]) -> AssumptionService:
    """
    Build the service owning the assumptions.

    :param provider: Owner of the shared motor client.
    :return: The service owning the assumptions.
    """
    return AssumptionService(
        assumptions=AssumptionRepository(provider=provider),
        schemas=SchemaRepository(provider=provider),
        industries=IndustryRepository(provider=provider),
    )


# ----- CONSTS ----- #

IndustryServiceDependency = Annotated[IndustryService, Depends(get_industry_service)]
SchemaServiceDependency = Annotated[SchemaService, Depends(get_schema_service)]
AssumptionServiceDependency = Annotated[AssumptionService, Depends(get_assumption_service)]
MongoProviderDependency = Annotated[MongoProvider, Depends(get_mongo_provider)]
