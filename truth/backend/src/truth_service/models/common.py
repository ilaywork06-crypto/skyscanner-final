"""
The payload pieces shared by more than one resource of the register.

:date: 2026-09-08
"""
# ----- IMPORTS ----- #

from pydantic import BaseModel, ConfigDict, Field, JsonValue

# ----- CLASSES ----- #


class IndustryReference(BaseModel):
    """
    An industry as it appears inside a schema or an assumption, which is its identifier and its name.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the industry")
    name: str = Field(description="Name of the industry")


class SchemaReference(BaseModel):
    """
    A declaration as it appears on an assumption, which is what a row names it by.

    The revision travels with it because an assumption is written against the declaration as it stood, and a
    row that named only the identifier could not say which of its revisions that was.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the declaration")
    name: str = Field(description="Name of the declaration")
    revision: int = Field(default=1, description="Revision the assumption was written against")


class SchemeResponse(BaseModel):
    """
    A declaration on its way out, which always spells the constraint list the one way.

    The original service read the list under ``constrains`` and answered with ``constraints``. Both are
    accepted on the way in, and this is the one that is ever written on the way out.
    """

    model_config = ConfigDict(populate_by_name=True)

    fields: list[dict[str, JsonValue]] = Field(default_factory=list, description="The attributes declared")
    constraints: list[dict[str, JsonValue]] = Field(
        default_factory=list,
        description="The rules the declared attributes are checked against",
    )


class SchemeRequest(BaseModel):
    """
    A declaration on its way in, which accepts either spelling of the constraint list.
    """

    model_config = ConfigDict(populate_by_name=True)

    fields: list[dict[str, JsonValue]] = Field(default_factory=list, description="The attributes declared")
    constraints: list[dict[str, JsonValue]] = Field(default_factory=list, description="The rules, spelled one way")
    constrains: list[dict[str, JsonValue]] = Field(default_factory=list, description="The rules, spelled the other")

    def rules(self) -> list[dict[str, JsonValue]]:
        """
        Read the constraint list whichever of the two spellings the caller used.

        :return: The rules the declaration carries.
        """
        return self.constraints or self.constrains


class IdentifierResponse(BaseModel):
    """
    What a write answers with, which is the identifier the register gave the thing that was written.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Identifier of the document that was written")
