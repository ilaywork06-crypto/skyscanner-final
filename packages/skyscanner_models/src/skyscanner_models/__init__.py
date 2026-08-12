"""
Shared pydantic API models that describe every payload exchanged between the Skyscanner services and the web client.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_models.common import (
    Artifact,
    MetadataAttribute,
    ObjectTypeReference,
    OperationResult,
    UserContext,
)
from skyscanner_models.entity import (
    EntityCreateRequest,
    EntityResponse,
    EntityUpdateRequest,
    EntityTypeCreateRequest,
    EntityTypeResponse,
    EntityTypeUpdateRequest,
)
from skyscanner_models.enums import (
    ArtifactKind,
    EntityStatus,
    EventStatus,
    FieldScope,
    FieldType,
    ParseState,
    Permission,
    Role,
    SortDirection,
    UploadSource,
)
from skyscanner_models.event import (
    EventCreateRequest,
    EventResponse,
    EventSummaryResponse,
    EventUpdateRequest,
    EventTypeCreateRequest,
    EventTypeResponse,
    EventTypeUpdateRequest,
)
from skyscanner_models.field import (
    FieldConstraint,
    FieldCreateRequest,
    FieldMetadata,
    FieldResponse,
    FieldUpdateRequest,
)
from skyscanner_models.grid import (
    ColumnDefinition,
    EventExportRequest,
    GridConfiguration,
    GridRowsRequest,
    GridRowsResponse,
)
from skyscanner_models.pagination import Page, PageRequest
from skyscanner_models.query import FilterCondition, FilterOperator, SearchQuery, SortSpecification
from skyscanner_models.storage import (
    ArtifactUploadResponse,
    DownloadLinkResponse,
    StorageObjectResponse,
)
from skyscanner_models.subscription import (
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionTrigger,
)
from skyscanner_models.industry import IndustryCreateRequest, IndustryResponse, IndustryUpdateRequest
from skyscanner_models.revision import FieldChange, RevisionResponse
from skyscanner_models.template import TemplateColumn, TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest
