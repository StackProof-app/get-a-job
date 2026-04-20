"""ATS adapters registry package.

Phase 11-13 add greenhouse, ashby, lever adapters alongside this one.
"""

from .generic_llm import GenericLLMAdapter
from .greenhouse import GreenhouseAdapter

__all__ = ["GenericLLMAdapter", "GreenhouseAdapter"]
