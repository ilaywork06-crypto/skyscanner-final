"""
The configuration of the register, which is the document store it is kept in and nothing else.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from functools import lru_cache

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pydantic_settings import BaseSettings

from skyscanner_common.settings import MongoSettings

# ----- CLASSES ----- #


class TruthServiceSettings(BaseSettings):
    """
    What the register needs to know about itself that the requests reaching it cannot say.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # The gateway in front of the register strips the prefix it forwards under, so what arrives is the bare
    # resource path - which is what the routes here are written as. Nothing in the request says what was
    # taken off, so the addresses the documentation page writes for itself have to be told.
    root_path: str = Field(default="", validation_alias="TRUTH_ROOT_PATH")


class TruthMongoSettings(MongoSettings):
    """
    Where the register is kept, which is the shared document store under a database of its own.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    database: str = Field(default="truth", validation_alias="MONGO_DATABASE")


# ----- FUNCTIONS ----- #


@lru_cache(maxsize=1)
def get_truth_service_settings() -> TruthServiceSettings:
    """
    Build the service settings once and reuse them for the whole process life time.

    :return: The cached service settings of the register.
    """
    return TruthServiceSettings()


@lru_cache(maxsize=1)
def get_truth_mongo_settings() -> TruthMongoSettings:
    """
    Build the document store settings once and reuse them for the whole process life time.

    :return: The cached document store settings of the register.
    """
    return TruthMongoSettings()
