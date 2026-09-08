"""
The fixed vocabulary of the storage service - its name, the key layout of the bucket and the streaming defaults.

:date: 2026-08-11
:author: t_beatrice
"""
# ----- CONSTS ----- #

SERVICE_NAME: str = "storage-service"
SERVICE_VERSION: str = "0.1.0"
SERVICE_DESCRIPTION: str = "Uploads, downloads and temporary links for every file the inventory refers to"

DEFAULT_OWNER_KIND: str = "events"
DEFAULT_CONTENT_TYPE: str = "application/octet-stream"
UNKNOWN_OWNER: str = "unassigned"

# The type a preview is served under once the file was recognised as text shaped. A browser handed a text/csv
# or an application/octet-stream body saves it to disk instead of rendering it, which is what turns a click on
# a file in the viewer into a download; text/plain is the one type every browser is willing to show.
INLINE_TEXT_CONTENT_TYPE: str = "text/plain; charset=utf-8"

# The types a browser renders on its own, which are therefore the only ones a preview leaves untouched.
IMAGE_CONTENT_TYPE_PREFIX: str = "image/"
PDF_CONTENT_TYPE: str = "application/pdf"

TEXT_CONTENT_TYPE_PREFIX: str = "text/"
TEXT_CONTENT_TYPE_SUFFIXES: tuple[str, ...] = ("+json", "+xml", "+yaml")
TEXT_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/csv",
        "application/javascript",
        "application/json",
        "application/ld+json",
        "application/ndjson",
        "application/sql",
        "application/toml",
        "application/x-ndjson",
        "application/x-sh",
        "application/x-yaml",
        "application/xml",
        "application/yaml",
    },
)

# What a browser was told about a file and what the file actually is drift apart constantly: a log uploaded
# from a script arrives as application/octet-stream and a csv arrives under a type nobody renders. The suffix
# is the second opinion, and the list mirrors the one the file viewer of the web client decides with.
TEXT_FILE_SUFFIXES: frozenset[str] = frozenset(
    {
        "cfg",
        "conf",
        "csv",
        "ini",
        "js",
        "json",
        "jsonl",
        "log",
        "md",
        "ndjson",
        "properties",
        "py",
        "sh",
        "sql",
        "toml",
        "ts",
        "tsv",
        "txt",
        "xml",
        "yaml",
        "yml",
    },
)
