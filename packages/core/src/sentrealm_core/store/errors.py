"""Workspace store errors mapped to HTTP status codes in the API layer."""


class WorkspaceStoreError(Exception):
    """Base error for workspace persistence."""


class NotFoundError(WorkspaceStoreError):
    """Project or document does not exist."""


class ConflictError(WorkspaceStoreError):
    """Delete or mutation blocked by workspace invariants."""
