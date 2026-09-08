"""
The names the service addresses its collections and its documents by, kept in one place.

:date: 2026-09-08
"""
# ----- CONSTS ----- #

SERVICE_NAME: str = "truth-service"

INDUSTRIES_COLLECTION: str = "industries"
SCHEMAS_COLLECTION: str = "schemas"
ASSUMPTIONS_COLLECTION: str = "assumptions"

IDENTIFIER_FIELD: str = "_id"

# Every revision of one declaration carries the identifier of the first of them, which is what groups a
# lineage together. A revision is addressed by its own identifier; a lineage is addressed by this one.
LINEAGE_FIELD: str = "lineage"
LATEST_FIELD: str = "latest_revision"

# The blob every searchable attribute of an assumption is folded into when it is written. Searching one
# indexed field is what keeps a search over a hundred thousand assumptions off a collection scan.
SEARCH_FIELD: str = "search_text"

# Where the attributes a schema declared are stored on an assumption. A filter names an attribute by its
# bare key, so anything that is not an attribute of the assumption itself is looked for under here.
VALUES_PREFIX: str = "values."

# The first revision of anything written into the register.
FIRST_REVISION: int = 1
