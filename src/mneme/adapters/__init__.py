"""Read-only integration adapters for MNEME v0.1."""

from .claude import ClaudeGlobalMemoryAdapter, ClaudeGlobalProjectionResult

__all__ = ("ClaudeGlobalMemoryAdapter", "ClaudeGlobalProjectionResult")
