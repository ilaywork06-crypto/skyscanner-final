"""
The rule about the identity of the files attached to one owner - the same name in the same folder, only once.

:date: 2026-08-26
:author: t_beatrice
"""
# ----- IMPORTS ----- #

from skyscanner_common.errors import ValidationError
from skyscanner_models.common import Artifact

# ----- FUNCTIONS ----- #


def require_unique_artifacts(artifacts: list[Artifact], label: str) -> None:
    """
    Refuse a set of files that holds the same name twice inside the same folder.

    The key in the bucket says nothing about this: every upload is written under a fresh identifier so that
    two uploads can never overwrite one another, which is what lets the very same file be attached to one
    event twice over. What a reader means by the same file is the name it carries in the folder it was filed
    under, and an owner holding two of those ends up with two records nobody can tell apart - one of which is
    unreachable in every listing that groups by name. Only the caller knows which of the two they meant, so
    the second one is refused rather than resolved here.

    :param artifacts: Files that would end up attached to one owner under one role.
    :param label: What the set is called, reported with a refusal so the caller knows which list was wrong.
    :raises ValidationError: When two of the files share a folder and a name.
    """
    seen: set[tuple[str, str]] = set()
    repeated: list[str] = []
    for artifact in artifacts:
        key = (artifact.folder or "", artifact.name)
        if key in seen:
            repeated.append(artifact.name)
            continue
        seen.add(key)

    if repeated:
        raise ValidationError(
            message="The same file cannot be attached twice under the same name",
            details={"files": ", ".join(sorted(set(repeated))), "attached_to": label},
        )
