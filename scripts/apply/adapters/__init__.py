"""ATS adapters registry package.

Phase 11-13 add greenhouse, ashby, lever adapters alongside this one.
"""

from .ashby import AshbyAdapter
from .generic_llm import GenericLLMAdapter
from .greenhouse import GreenhouseAdapter

__all__ = ["AshbyAdapter", "GenericLLMAdapter", "GreenhouseAdapter"]
