"""Section template catalog."""

from page.catalog.instantiate import TemplateInstantiationError, instantiate_section
from page.catalog.templates import (
    SECTION_TEMPLATES,
    get_section_template,
    get_section_variant,
    list_section_templates,
)

__all__ = [
    "SECTION_TEMPLATES",
    "TemplateInstantiationError",
    "get_section_template",
    "get_section_variant",
    "instantiate_section",
    "list_section_templates",
]
