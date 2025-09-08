"""JSON schemas for document structure validation."""

import json
from typing import Any

# Document structure JSON schema
DOCUMENT_STRUCTURE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pdf-accessibility.com/schemas/document-structure.json",
    "title": "PDF Document Structure Schema",
    "description": "Schema for PDF accessibility document structure",
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "string",
            "description": "Unique document identifier",
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "title": {
            "type": ["string", "null"],
            "description": "Document title",
            "maxLength": 500
        },
        "language": {
            "type": "string",
            "description": "Primary document language",
            "pattern": "^[a-z]{2}(-[A-Z]{2})?$",
            "default": "en"
        },
        "total_pages": {
            "type": "integer",
            "description": "Total number of pages",
            "minimum": 1
        },
        "elements": {
            "type": "array",
            "description": "All document elements",
            "items": {
                "$ref": "#/$defs/DocumentElement"
            }
        },
        "reading_order": {
            "type": "array",
            "description": "Reading order by element IDs",
            "items": {
                "type": "string",
                "pattern": "^[a-f0-9-]{36}$"
            }
        },
        "toc_elements": {
            "type": "array",
            "description": "Table of contents element IDs",
            "items": {
                "type": "string",
                "pattern": "^[a-f0-9-]{36}$"
            }
        },
        "metadata": {
            "type": "object",
            "description": "Document metadata",
            "properties": {
                "analysis_method": {
                    "type": "string",
                    "enum": ["bedrock_claude", "textract_only", "manual"]
                },
                "textract_available": {
                    "type": "boolean"
                },
                "processing_time": {
                    "type": "number",
                    "minimum": 0
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                }
            }
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "Creation timestamp"
        },
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "Last update timestamp"
        }
    },
    "required": ["doc_id", "total_pages", "elements"],
    "$defs": {
        "BoundingBox": {
            "type": "object",
            "description": "Normalized bounding box coordinates",
            "properties": {
                "left": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "top": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "width": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "height": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                }
            },
            "required": ["left", "top", "width", "height"]
        },
        "DocumentElement": {
            "type": "object",
            "description": "Base document element",
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[a-f0-9-]{36}$",
                    "description": "Unique element identifier"
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "heading", "paragraph", "list", "list_item",
                        "table", "table_row", "table_cell", "figure",
                        "caption", "footer", "header", "sidebar", "quote", "code"
                    ]
                },
                "page_number": {
                    "type": "integer",
                    "minimum": 1
                },
                "bounding_box": {
                    "oneOf": [
                        {"$ref": "#/$defs/BoundingBox"},
                        {"type": "null"}
                    ]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.8
                },
                "text": {
                    "type": "string",
                    "description": "Text content of the element"
                },
                "children": {
                    "type": "array",
                    "items": {
                        "$ref": "#/$defs/DocumentElement"
                    }
                },
                "metadata": {
                    "type": "object"
                }
            },
            "required": ["id", "type", "page_number", "text"],
            "allOf": [
                {
                    "if": {
                        "properties": {"type": {"const": "heading"}}
                    },
                    "then": {
                        "properties": {
                            "level": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 6
                            }
                        },
                        "required": ["level"]
                    }
                },
                {
                    "if": {
                        "properties": {"type": {"const": "list"}}
                    },
                    "then": {
                        "properties": {
                            "list_type": {
                                "type": "string",
                                "enum": ["unordered", "ordered", "definition"]
                            },
                            "start_number": {
                                "type": ["integer", "null"],
                                "minimum": 1
                            }
                        }
                    }
                },
                {
                    "if": {
                        "properties": {"type": {"const": "list_item"}}
                    },
                    "then": {
                        "properties": {
                            "marker": {
                                "type": ["string", "null"]
                            },
                            "item_number": {
                                "type": ["integer", "null"]
                            }
                        }
                    }
                },
                {
                    "if": {
                        "properties": {"type": {"const": "table"}}
                    },
                    "then": {
                        "properties": {
                            "rows": {
                                "type": "integer",
                                "minimum": 1
                            },
                            "columns": {
                                "type": "integer",
                                "minimum": 1
                            },
                            "has_header": {
                                "type": "boolean"
                            },
                            "caption": {
                                "type": ["string", "null"]
                            },
                            "summary": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": ["rows", "columns"]
                    }
                },
                {
                    "if": {
                        "properties": {"type": {"const": "table_cell"}}
                    },
                    "then": {
                        "properties": {
                            "row_index": {
                                "type": "integer",
                                "minimum": 0
                            },
                            "column_index": {
                                "type": "integer",
                                "minimum": 0
                            },
                            "row_span": {
                                "type": "integer",
                                "minimum": 1
                            },
                            "column_span": {
                                "type": "integer",
                                "minimum": 1
                            },
                            "is_header": {
                                "type": "boolean"
                            },
                            "scope": {
                                "type": ["string", "null"],
                                "enum": ["row", "col", "rowgroup", "colgroup", null]
                            }
                        },
                        "required": ["row_index", "column_index"]
                    }
                },
                {
                    "if": {
                        "properties": {"type": {"const": "figure"}}
                    },
                    "then": {
                        "properties": {
                            "figure_type": {
                                "type": "string",
                                "enum": [
                                    "image", "chart", "diagram", "graph",
                                    "illustration", "photo", "screenshot", "map", "other"
                                ]
                            },
                            "alt_text": {
                                "type": ["string", "null"],
                                "maxLength": 250
                            },
                            "caption": {
                                "type": ["string", "null"]
                            },
                            "title": {
                                "type": ["string", "null"]
                            },
                            "long_description": {
                                "type": ["string", "null"]
                            },
                            "image_url": {
                                "type": ["string", "null"]
                            }
                        }
                    }
                }
            ]
        }
    }
}

# Alt text data schema
ALT_TEXT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pdf-accessibility.com/schemas/alt-text.json",
    "title": "Alt Text Data Schema",
    "description": "Schema for alternative text descriptions",
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "figures": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/FigureAltText"
            }
        },
        "generated_at": {
            "type": "string",
            "format": "date-time"
        },
        "generation_method": {
            "type": "string",
            "enum": ["bedrock_vision", "bedrock_claude", "rekognition", "manual"]
        },
        "total_figures": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": ["doc_id", "figures"],
    "$defs": {
        "FigureAltText": {
            "type": "object",
            "properties": {
                "figure_id": {
                    "type": "string",
                    "pattern": "^[a-f0-9-]{36}$"
                },
                "alt_text": {
                    "type": "string",
                    "maxLength": 250
                },
                "description_type": {
                    "type": "string",
                    "enum": ["decorative", "informative", "complex"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "generation_method": {
                    "type": "string",
                    "enum": ["bedrock_vision", "bedrock_claude", "rekognition", "manual"]
                },
                "long_description": {
                    "type": ["string", "null"]
                },
                "context_used": {
                    "type": "string"
                }
            },
            "required": ["figure_id", "alt_text", "confidence"]
        }
    }
}

# Validation results schema
VALIDATION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pdf-accessibility.com/schemas/validation.json",
    "title": "Accessibility Validation Schema",
    "description": "Schema for accessibility validation results",
    "type": "object",
    "properties": {
        "doc_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "validation_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        },
        "compliance_level": {
            "type": "string",
            "enum": ["AA", "A", "Non-compliant"]
        },
        "pdf_ua_compliant": {
            "type": "boolean"
        },
        "wcag_version": {
            "type": "string",
            "enum": ["2.0", "2.1", "2.2"]
        },
        "issues": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/ValidationIssue"
            }
        },
        "validated_at": {
            "type": "string",
            "format": "date-time"
        },
        "validation_tools": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["doc_id", "validation_score", "issues"],
    "$defs": {
        "ValidationIssue": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "missing_alt_text", "improper_heading_hierarchy",
                        "color_contrast", "missing_table_headers",
                        "improper_reading_order", "missing_language",
                        "missing_title", "unlabeled_form_field"
                    ]
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning", "info"]
                },
                "message": {
                    "type": "string"
                },
                "location": {
                    "type": ["string", "null"]
                },
                "element_id": {
                    "type": ["string", "null"]
                },
                "wcag_criterion": {
                    "type": ["string", "null"],
                    "pattern": "^\\d+\\.\\d+\\.\\d+$"
                },
                "recommendation": {
                    "type": ["string", "null"]
                },
                "help_url": {
                    "type": ["string", "null"],
                    "format": "uri"
                }
            },
            "required": ["type", "severity", "message"]
        }
    }
}


def get_schema_by_name(schema_name: str) -> dict[str, Any]:
    """Get JSON schema by name.
    
    Args:
        schema_name: Name of the schema
        
    Returns:
        JSON schema dictionary
        
    Raises:
        ValueError: If schema name is not found
    """
    schemas = {
        'document_structure': DOCUMENT_STRUCTURE_SCHEMA,
        'alt_text': ALT_TEXT_SCHEMA,
        'validation': VALIDATION_SCHEMA
    }

    if schema_name not in schemas:
        raise ValueError(f"Unknown schema: {schema_name}")

    return schemas[schema_name]


def export_schemas_to_file(output_path: str) -> None:
    """Export all schemas to a JSON file.
    
    Args:
        output_path: Path to output file
    """
    all_schemas = {
        'document_structure': DOCUMENT_STRUCTURE_SCHEMA,
        'alt_text': ALT_TEXT_SCHEMA,
        'validation': VALIDATION_SCHEMA
    }

    with open(output_path, 'w') as f:
        json.dump(all_schemas, f, indent=2)
