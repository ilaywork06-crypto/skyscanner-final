"""
The rules around the dynamic schema - declaring fields for an industry and validating the values supplied for them.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

import re
from datetime import datetime
from typing import Any, Mapping

from pydantic import ValidationError as PydanticValidationError

from skyscanner_common.datetime_utils import ensure_utc, utc_now
from skyscanner_common.errors import ConflictError, NotFoundError, ValidationError
from skyscanner_models.common import Coordinate, MetadataAttribute, UserContext
from skyscanner_models.enums import DependencyOperator, FieldScope, FieldType
from skyscanner_models.field import (
    FieldCreateRequest,
    FieldDependency,
    FieldResponse,
    FieldUpdateRequest,
)

from events_service.documents import FieldDocument
from events_service.repositories.field_repository import FieldRepository

# ----- CONSTS ----- #

TRUE_VALUES: frozenset[str] = frozenset({"true", "1", "yes", "on"})
FALSE_VALUES: frozenset[str] = frozenset({"false", "0", "no", "off"})

# ----- CLASSES ----- #


class FieldService:
    """
    Owner of the dynamic schema, both of the declarations themselves and of the values that follow them.
    """

    def __init__(self, repository: FieldRepository) -> None:
        """
        Bind the service to the repository of the field declarations.

        :param repository: Persistence of the field declarations.
        """
        self._repository = repository

    async def list_fields(
        self,
        scope: FieldScope,
        industry: str | None = None,
        entity_type: str | None = None,
        include_shared: bool = True,
        additional: bool | None = None,
        offset: int = 0,
        limit: int = 0,
    ) -> list[FieldResponse]:
        """
        Read the declarations that apply to a scope, so that the client can render the matching schema.

        :param scope: Whether the declarations target events or entities.
        :param industry: Industry whose own declarations are added to the shared ones.
        :param entity_type: Entity type the declarations are limited to.
        :param include_shared: Whether the declarations that belong to no industry are included.
        :param additional: Which half of the form is read, both halves when it is left open.
        :param offset: Amount of declarations skipped before collecting.
        :param limit: Largest amount of declarations that is returned, zero for all of them.
        :return: The matching declarations ordered by their relative position.
        """
        documents = await self._repository.list_for_scope(
            scope=scope,
            industry=industry,
            entity_type=entity_type,
            include_shared=include_shared,
            additional=additional,
            offset=offset,
            limit=limit,
        )

        return [document.to_response() for document in documents]

    async def create_field(self, request: FieldCreateRequest, user: UserContext) -> FieldResponse:
        """
        Declare a new dynamic field for an industry, refusing a key that the very same scope already holds.

        :param request: Declaration supplied by the user.
        :param user: Identity the declaration is attributed to.
        :return: The stored declaration.
        :raises ConflictError: When the scope already holds a field with the same key.
        """
        existing = await self._repository.find_by_key(
            scope=request.scope,
            key=request.key,
            industry=request.industry,
            entity_type=request.entity_type,
        )
        if existing is not None:
            raise ConflictError(
                message="A field with this key is already declared for the industry",
                details={"key": request.key, "scope": request.scope.value},
            )

        document = FieldDocument(**request.model_dump(), created_by=user.username)
        await self._repository.insert(document=document)

        return document.to_response()

    async def update_field(self, field_id: str, request: FieldUpdateRequest) -> FieldResponse:
        """
        Change a stored declaration, leaving every attribute the caller omitted untouched.

        :param field_id: Identifier of the declaration that is changed.
        :param request: Attributes the caller wants to change.
        :return: The changed declaration.
        :raises NotFoundError: When the identifier is unknown.
        """
        document = await self._repository.find_by_id(identifier=field_id)
        if document is None:
            raise NotFoundError(message="The field declaration does not exist", details={"id": field_id})

        updates = request.model_dump(exclude_unset=True, exclude_none=True)
        updates["updated_at"] = utc_now()
        await self._repository.update_fields(identifier=field_id, updates=updates)

        refreshed = await self._repository.find_by_id(identifier=field_id)
        if refreshed is None:
            raise NotFoundError(message="The field declaration does not exist", details={"id": field_id})

        return refreshed.to_response()

    async def delete_field(self, field_id: str, user: UserContext) -> None:
        """
        Remove a stored declaration, which hides the generated column without touching the stored values.

        :param field_id: Identifier of the declaration that is removed.
        :param user: Identity the removal is attributed to.
        :raises NotFoundError: When the identifier is unknown.
        """
        removed = await self._repository.delete(identifier=field_id, user=user.username)
        if not removed:
            raise NotFoundError(message="The field declaration does not exist", details={"id": field_id})

    async def build_values(
        self,
        scope: FieldScope,
        supplied: list[MetadataAttribute],
        industry: str | None = None,
        entity_type: str | None = None,
        context: dict[str, Any] | None = None,
        asked: set[str] | None = None,
        carried: set[str] | None = None,
    ) -> tuple[list[MetadataAttribute], dict[str, Any]]:
        """
        Validate the values a user supplied against the declared schema and shape them for storage.

        Every value has to follow a declaration. A key nobody declared used to be accepted, stored and turned
        into a column of its own, which is how two people describing the same thing ended up writing
        sample_rate and sampling_rate onto neighbouring rows and how columns appeared that nobody remembered
        creating. A key that no declaration covers is therefore refused, and the answer to a value that ought
        to be recorded is to declare the field for it rather than to invent the key on the spot.

        :param scope: Whether the values belong to an event or to an entity.
        :param supplied: Values the user supplied, keyed by the field they belong to.
        :param industry: Industry whose declarations apply on top of the shared ones.
        :param entity_type: Entity type the declarations are limited to.
        :param context: Values of the object this form hangs under, which its dependencies may point at.
        :param asked: Declared keys this particular form asks for, empty when it asks for all of them. A
            declaration the form never showed cannot be required by it, but a value supplied for one is
            still measured against its declaration.
        :param carried: Undeclared keys the object already holds, which are kept rather than refused. What
            was written before the rule existed stays readable and editable; nothing new joins it.
        :return: The validated attributes and the flattened mapping used for queries.
        :raises ValidationError: When a required value is missing, a value breaks a declared rule, or a value
            was supplied under a key no declaration covers.
        """
        declarations = await self._repository.list_for_scope(scope=scope, industry=industry, entity_type=entity_type)
        by_key = {declaration.key: declaration for declaration in declarations}
        supplied_by_key = {attribute.key: attribute for attribute in supplied}

        attributes: list[MetadataAttribute] = []
        flattened: dict[str, Any] = {}

        # What the caller actually filled in, which is what the dependencies of the other fields are read
        # against. A field whose dependency does not hold is not part of this form at all, so it is neither
        # required nor stored - the client hides it for the same reason.
        supplied_values = {key: attribute.value for key, attribute in supplied_by_key.items()}

        for key, declaration in by_key.items():
            on_form = asked is None or key in asked
            if not on_form and key not in supplied_by_key:
                continue

            if not dependencies_hold(
                dependencies=declaration.depends_on,
                values=supplied_values,
                context=context,
            ):
                continue

            raw_value = supplied_by_key[key].value if key in supplied_by_key else declaration.default
            if _is_empty(raw_value):
                if declaration.required and on_form:
                    raise ValidationError(
                        message=f"The field {declaration.name} is required",
                        details={"key": key},
                    )
                continue

            stored = _coerce(declaration=declaration, value=raw_value)
            _check_constraints(declaration=declaration, value=stored)
            flattened[key] = stored
            attributes.append(MetadataAttribute(key=key, value=_to_json_value(stored), type=declaration.type))

        undeclared = [
            key for key, attribute in supplied_by_key.items() if key not in by_key and not _is_empty(attribute.value)
        ]
        _require_declared(keys=undeclared, allowed=carried or set(), scope=scope)

        for key in undeclared:
            attribute = supplied_by_key[key]
            flattened[key] = attribute.value
            attributes.append(MetadataAttribute(key=key, value=attribute.value, type=attribute.type))

        return attributes, flattened


# ----- FUNCTIONS ----- #


def _require_declared(keys: list[str], allowed: set[str], scope: FieldScope) -> None:
    """
    Refuse values written under keys that no declaration covers.

    :param keys: Keys the caller supplied that no declaration covers.
    :param allowed: Keys the object already holds, which are carried rather than refused.
    :param scope: Whether the values belong to an event or to an entity, reported with a refusal.
    :raises ValidationError: When one of the keys is neither declared nor already stored.
    """
    refused = sorted(key for key in keys if key not in allowed)
    if not refused:
        return

    raise ValidationError(
        message="Every value has to follow a field declared on the Schema page",
        details={"keys": ", ".join(refused), "scope": scope.value},
    )


def dependencies_hold(
    dependencies: list[FieldDependency],
    values: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> bool:
    """
    Decide whether every condition a field declared on the fields around it currently holds.

    A field with no declared dependency always applies. When it declared several, all of them have to hold,
    which is the reading that lets a schema narrow a field down step by step.

    :param dependencies: Conditions the field declared on other fields.
    :param values: Values the caller supplied for the other fields of the same form.
    :param context: Values of the owning object, which a dependency may point at across the two scopes.
    :return: Whether the field applies to the form as it currently stands.
    """
    return all(
        _dependency_holds(dependency=dependency, values=values, context=context) for dependency in dependencies
    )


def _dependency_holds(
    dependency: FieldDependency,
    values: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> bool:
    """
    Test one condition against the value the field it points at currently holds.

    :param dependency: Condition declared on another field.
    :param values: Values the caller supplied for the other fields of the same form.
    :param context: Values of the owning object, which a dependency may point at across the two scopes.
    :return: Whether the condition holds.
    """
    other = _resolve_value(key=dependency.field, values=values, context=context)
    filled = not _is_empty(other)

    if dependency.operator is DependencyOperator.HAS_VALUE:
        return filled

    if dependency.operator is DependencyOperator.IS_EMPTY:
        return not filled

    if dependency.operator is DependencyOperator.NOT_EQUALS:
        return other not in dependency.values

    # Both equals and one of compare against the declared values; equals simply declares a single one.
    return other in dependency.values


def _resolve_value(key: str, values: dict[str, Any], context: dict[str, Any] | None) -> Any:
    """
    Read the value a condition is tested against, looking at the form itself before its surroundings.

    An entity field is allowed to depend on a field of the event it hangs under, so a key the form itself
    does not declare is looked up in the values of that event. The form wins whenever it holds the key at
    all, even with nothing filled in, because a field of the form is the one the user is looking at.

    :param key: Key of the field the condition points at.
    :param values: Values the caller supplied for the other fields of the same form.
    :param context: Values of the owning object, empty when the form hangs under nothing.
    :return: The value the condition is tested against, or nothing when neither side holds the key.
    """
    if key in values:
        return values[key]

    return (context or {}).get(key)


def _is_empty(value: Any) -> bool:
    """
    Decide whether a supplied value counts as missing.

    :param value: Value the user supplied for a field.
    :return: Whether the value has to be treated as missing.
    """
    return value is None or value == "" or value == []


def _coerce(declaration: FieldDocument, value: Any) -> Any:
    """
    Turn a supplied value into the shape the declared type asks for.

    :param declaration: Declaration the value belongs to.
    :param value: Value the user supplied.
    :return: The value in the shape it is stored in.
    :raises ValidationError: When the value cannot be read as the declared type.
    """
    if declaration.array:
        candidates = value if isinstance(value, list) else [value]
        return [_coerce_single(declaration=declaration, value=candidate) for candidate in candidates]

    return _coerce_single(declaration=declaration, value=value)


def _coerce_single(declaration: FieldDocument, value: Any) -> Any:
    """
    Turn one scalar value into the shape the declared type asks for.

    :param declaration: Declaration the value belongs to.
    :param value: Scalar value the user supplied.
    :return: The scalar value in the shape it is stored in.
    :raises ValidationError: When the value cannot be read as the declared type.
    """
    field_type = declaration.type
    try:
        if field_type in {FieldType.STRING, FieldType.TEXT, FieldType.ENUM}:
            return str(value)
        if field_type is FieldType.INTEGER:
            return int(value)
        if field_type is FieldType.NUMBER:
            return float(value)
        if field_type is FieldType.BOOLEAN:
            return _coerce_boolean(value=value)
        if field_type in {FieldType.DATE, FieldType.DATETIME}:
            return _coerce_datetime(value=value)
        if field_type is FieldType.COORDINATE:
            return _coerce_coordinate(value=value)
    except (TypeError, ValueError, PydanticValidationError) as error:
        raise ValidationError(
            message=f"The value of {declaration.name} is not a valid {field_type.value}",
            details={"key": declaration.key},
        ) from error

    return value


def _coerce_boolean(value: Any) -> bool:
    """
    Read a supplied value as a truth value, accepting the usual text spellings.

    :param value: Value the user supplied.
    :return: The truth value the input stands for.
    :raises ValueError: When the input does not spell a truth value.
    """
    if isinstance(value, bool):
        return value

    lowered = str(value).strip().lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False

    raise ValueError(f"{value} is not a truth value")


def _coerce_datetime(value: Any) -> datetime:
    """
    Read a supplied value as a timezone aware UTC moment.

    :param value: Value the user supplied.
    :return: The moment expressed in UTC.
    :raises ValueError: When the input does not spell a moment.
    """
    if isinstance(value, datetime):
        converted = ensure_utc(value)
    else:
        converted = ensure_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))

    if converted is None:
        raise ValueError(f"{value} is not a moment")

    return converted


def _coerce_coordinate(value: Any) -> dict[str, Any]:
    """
    Read a supplied value as a point on the globe, whatever shape the caller wrote it in.

    A map picker hands back the three numbers by name, while a script is more likely to write the pair or the
    triple as a list, so both are accepted and both are stored the same way.

    :param value: Value the user supplied.
    :return: The point as the three named numbers it is stored as.
    :raises ValueError: When the input does not spell a point.
    """
    if isinstance(value, (list, tuple)):
        if len(value) not in {2, 3}:
            raise ValueError(f"{value} is not a coordinate")
        lon, lat, *rest = value
        return Coordinate(lon=float(lon), lat=float(lat), alt=float(rest[0]) if rest else None).model_dump()

    if isinstance(value, Mapping):
        return Coordinate.model_validate(dict(value)).model_dump()

    raise ValueError(f"{value} is not a coordinate")


def _check_constraints(declaration: FieldDocument, value: Any) -> None:
    """
    Verify that a stored value satisfies every rule the declaration carries.

    :param declaration: Declaration the value belongs to.
    :param value: Value in the shape it is stored in.
    :raises ValidationError: When the value breaks a declared rule or leaves the allowed options.
    """
    if declaration.type is FieldType.ENUM and declaration.metadata.options:
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if str(candidate) not in declaration.metadata.options:
                raise ValidationError(
                    message=f"The value of {declaration.name} is not one of the allowed options",
                    details={"key": declaration.key, "value": str(candidate)},
                )

    for constraint in declaration.constraints:
        if not _satisfies(constraint_name=constraint.name, constraint_value=constraint.value, value=value):
            raise ValidationError(
                message=constraint.message or f"The value of {declaration.name} breaks the rule {constraint.name}",
                details={"key": declaration.key, "constraint": constraint.name},
            )


def _satisfies(constraint_name: str, constraint_value: Any, value: Any) -> bool:
    """
    Check one rule against a stored value.

    :param constraint_name: Name of the rule that is checked.
    :param constraint_value: Value the rule compares against.
    :param value: Value in the shape it is stored in.
    :return: Whether the value satisfies the rule.
    """
    if constraint_value is None:
        return True

    if constraint_name == "min" and isinstance(value, (int, float)):
        return bool(value >= float(constraint_value))
    if constraint_name == "max" and isinstance(value, (int, float)):
        return bool(value <= float(constraint_value))
    if constraint_name == "min_length":
        return len(str(value)) >= int(constraint_value)
    if constraint_name == "max_length":
        return len(str(value)) <= int(constraint_value)
    if constraint_name == "pattern":
        return re.fullmatch(str(constraint_value), str(value)) is not None

    return True


def _to_json_value(value: Any) -> Any:
    """
    Turn a stored value into a representation that survives the trip through the API as plain data.

    :param value: Value in the shape it is stored in.
    :return: The same value expressed with plain data types only.
    """
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [_to_json_value(item) for item in value]

    return value
