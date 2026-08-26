"""
Payloads describing the dynamic field definitions that shape events, entities, the create wizard and the grid columns.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skyscanner_models.enums import DependencyOperator, FieldScope, FieldType

# ----- CLASSES ----- #


class FieldConstraint(BaseModel):
    """
    A single validation rule attached to a dynamic field, such as a minimum value or a regular expression.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Name of the rule, for example min, max, pattern or min_length")
    value: JsonValue = Field(default=None, description="Value the rule compares against")
    message: str | None = Field(default=None, description="Message shown when the rule is violated")


class FieldDependency(BaseModel):
    """
    A condition on another field that decides whether this field applies at all.

    A field may depend on a sibling merely holding a value, or on it holding one of a set of values. Every
    declared dependency has to hold for the field to be asked for, which is what lets a schema say things
    like "the calibration file is only relevant once the sensor is one of these two".

    A field of an entity may also point at a field of the event that entity hangs under, because that event
    is the only other form whose values are known while the entity is filled in. The entity wins wherever
    both declare the same key, and an event field can only ever point at another field of its own event.
    """

    model_config = ConfigDict(populate_by_name=True)

    field: str = Field(description="Key of the field this one depends on, of the same form or of its event")
    operator: DependencyOperator = Field(
        default=DependencyOperator.HAS_VALUE,
        description="How the value of the other field is tested",
    )
    values: list[JsonValue] = Field(
        default_factory=list,
        description="Values the other field is compared against by the equals and one of operators",
    )


class FieldMetadata(BaseModel):
    """
    Extra descriptors that do not restrict the value but tell the client how the field should be rendered.
    """

    model_config = ConfigDict(populate_by_name=True)

    allowed_file_types: list[str] = Field(default_factory=list, description="Suffixes accepted by a file field")
    options: list[str] = Field(default_factory=list, description="Allowed values of an enum field")
    unit: str | None = Field(default=None, description="Physical unit appended to a numeric value")
    description: str | None = Field(default=None, description="Helper text shown next to the input")
    placeholder: str | None = Field(default=None, description="Placeholder shown while the input is empty")
    group: str | None = Field(default=None, description="Section the field is grouped under in the create wizard")


class FieldBase(BaseModel):
    """
    The attributes shared by the create, update and response representations of a dynamic field.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Label shown to the user for the field")
    key: str = Field(description="Machine key the value is stored under")
    type: FieldType = Field(default=FieldType.STRING, description="Primitive type the field holds")
    array: bool = Field(default=False, description="Whether the field holds a list of values")
    default: JsonValue = Field(default=None, description="Value used when the user leaves the field empty")
    required: bool = Field(default=False, description="Whether a value has to be supplied")
    scope: FieldScope = Field(default=FieldScope.EVENT, description="Whether the field belongs to events or entities")
    industry: str | None = Field(
        default=None,
        description="Industry key owning the field, empty when the field is shared",
    )
    entity_type: str | None = Field(default=None, description="Entity type key the field is limited to")
    # Which of the two halves of a form the field belongs to. The declared fields describe the object itself,
    # while the additional ones describe the free form block underneath it - the block users used to fill in
    # with keys of their own invention. Declaring those keys is what turns that block into a standard.
    additional: bool = Field(default=False, description="Whether the field belongs to the additional data block")
    metadata: FieldMetadata = Field(default_factory=FieldMetadata, description="Rendering descriptors of the field")
    constraints: list[FieldConstraint] = Field(default_factory=list, description="Validation rules of the field")
    depends_on: list[FieldDependency] = Field(
        default_factory=list,
        description="Conditions on other fields that all have to hold before this field applies",
    )
    filterable: bool = Field(default=True, description="Whether the generated grid column offers a filter")
    sortable: bool = Field(default=True, description="Whether the generated grid column can be sorted")
    editable: bool = Field(default=True, description="Whether the value may be changed after creation")
    visible: bool = Field(default=True, description="Whether the generated grid column is shown by default")
    order: int = Field(default=100, description="Relative position of the generated grid column")


class FieldCreateRequest(FieldBase):
    """
    The payload accepted when an industry declares a new dynamic field.
    """


class FieldUpdateRequest(BaseModel):
    """
    A partial update of a dynamic field, where every omitted attribute keeps its stored value.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="New label of the field")
    type: FieldType | None = Field(default=None, description="New primitive type of the field")
    array: bool | None = Field(default=None, description="New multiplicity of the field")
    default: JsonValue = Field(default=None, description="New fallback value of the field")
    required: bool | None = Field(default=None, description="New requiredness of the field")
    additional: bool | None = Field(default=None, description="New half of the form the field belongs to")
    metadata: FieldMetadata | None = Field(default=None, description="New rendering descriptors of the field")
    constraints: list[FieldConstraint] | None = Field(default=None, description="New validation rules of the field")
    depends_on: list[FieldDependency] | None = Field(default=None, description="New conditions on other fields")
    filterable: bool | None = Field(default=None, description="New filtering behaviour of the column")
    sortable: bool | None = Field(default=None, description="New sorting behaviour of the column")
    editable: bool | None = Field(default=None, description="New editability of the value")
    visible: bool | None = Field(default=None, description="New default visibility of the column")
    order: int | None = Field(default=None, description="New relative position of the column")


class FieldResponse(FieldBase):
    """
    A stored dynamic field definition as it is handed back to the client.
    """

    id: str = Field(description="Identifier of the field definition")
    # Nobody declared this one: it was read off the stored documents so that a value written by a script or
    # typed into the additional data block still reaches the table. Saying so is what stops a reader
    # wondering which colleague invented a column they have never seen a form ask for.
    discovered: bool = Field(
        default=False,
        description="Whether the definition was inferred from the stored documents rather than declared",
    )
    created_at: datetime = Field(description="UTC moment the field was declared")
    updated_at: datetime | None = Field(default=None, description="UTC moment the field last changed")
    created_by: str | None = Field(default=None, description="User that declared the field")
