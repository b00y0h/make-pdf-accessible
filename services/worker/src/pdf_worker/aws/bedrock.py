"""Bedrock client wrapper for Claude 3.5 integration with structured responses."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

from pdf_worker.core.config import config
from pdf_worker.core.exceptions import BedrockError, WorkerConfigError

logger = Logger()
tracer = Tracer()


class ClaudeModel(str, Enum):
    """Available Claude models in Bedrock."""

    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"


@dataclass
class BedrockUsage:
    """Token usage statistics from Bedrock."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class BedrockResponse:
    """Structured response from Bedrock Claude."""

    content: str
    usage: BedrockUsage
    model_id: str
    request_id: str

    def try_parse_json(self) -> dict[str, Any] | None:
        """Attempt to parse content as JSON.

        Returns:
            Parsed JSON data or None if parsing fails
        """
        try:
            # Try to find JSON within the response
            content = self.content.strip()

            # Look for JSON block markers
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()

            # Try to extract JSON from markdown code blocks
            elif content.startswith("```") and content.endswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            # Find JSON object boundaries
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)

            # Try parsing entire content
            return json.loads(content)

        except (json.JSONDecodeError, ValueError):
            return None


class BedrockClient:
    """Enhanced Bedrock client for Claude 3.5 integration."""

    def __init__(self, region_name: str | None = None) -> None:
        """Initialize Bedrock client.

        Args:
            region_name: AWS region name. Defaults to config.aws_region.
        """
        try:
            self._client = boto3.client(
                "bedrock-runtime", region_name=region_name or config.aws_region
            )
        except Exception as e:
            raise WorkerConfigError(f"Failed to initialize Bedrock client: {e}")

        logger.info(
            f"Initialized Bedrock client for region: {region_name or config.aws_region}"
        )

    @tracer.capture_method
    def invoke_claude(
        self,
        prompt: str,
        model_id: ClaudeModel = ClaudeModel.CLAUDE_3_5_SONNET,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        top_p: float = 0.9,
        system_prompt: str | None = None,
        stop_sequences: list[str] | None = None,
    ) -> BedrockResponse:
        """Invoke Claude model with enhanced error handling.

        Args:
            prompt: User prompt for Claude
            model_id: Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            stop_sequences: Optional stop sequences

        Returns:
            Structured Bedrock response

        Raises:
            BedrockError: If invocation fails
        """
        try:
            # Build message structure for Claude 3
            messages = [{"role": "user", "content": prompt}]

            # Build request payload
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": messages,
            }

            if system_prompt:
                request_body["system"] = system_prompt

            if stop_sequences:
                request_body["stop_sequences"] = stop_sequences

            # Invoke model
            response = self._client.invoke_model(
                modelId=model_id.value,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            # Extract usage information
            usage_data = response_body.get("usage", {})
            usage = BedrockUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0)
                + usage_data.get("output_tokens", 0),
            )

            # Extract content
            content = ""
            if "content" in response_body and response_body["content"]:
                content = response_body["content"][0].get("text", "")

            result = BedrockResponse(
                content=content,
                usage=usage,
                model_id=model_id.value,
                request_id=response.get("ResponseMetadata", {}).get("RequestId", ""),
            )

            logger.info(
                f"Claude invocation successful: {usage.total_tokens} tokens used"
            )
            logger.debug(f"Response preview: {content[:100]}...")

            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Handle specific error cases
            if error_code == "ValidationException":
                raise BedrockError(
                    "Invalid request parameters for Bedrock", model_id=model_id.value
                )
            elif error_code == "ModelNotReadyException":
                raise BedrockError(
                    f"Model {model_id.value} is not ready", model_id=model_id.value
                )
            elif error_code == "ThrottlingException":
                raise BedrockError(
                    "Request was throttled, try again later", model_id=model_id.value
                )

            raise BedrockError(
                f"Bedrock invocation failed: {error_code}",
                model_id=model_id.value,
                request_id=e.response.get("ResponseMetadata", {}).get("RequestId"),
            ) from e

        except json.JSONDecodeError as e:
            raise BedrockError(f"Failed to parse Bedrock response: {e}")

        except Exception as e:
            raise BedrockError(f"Unexpected Bedrock error: {e}")

    @tracer.capture_method
    def analyze_document_structure(
        self,
        document_text: str,
        textract_data: dict[str, Any] | None = None,
        custom_instructions: str | None = None,
    ) -> BedrockResponse:
        """Analyze document structure using Claude 3.5.

        Args:
            document_text: Full document text content
            textract_data: Optional Textract analysis results
            custom_instructions: Optional custom analysis instructions

        Returns:
            Structured analysis response
        """
        # Build context information
        context_info = []

        if textract_data:
            block_counts = {}
            for block in textract_data.get("blocks", []):
                block_type = block.get("BlockType")
                block_counts[block_type] = block_counts.get(block_type, 0) + 1

            context_info.append(f"Textract detected: {dict(block_counts)}")

        context = "\n".join(context_info) if context_info else ""

        # Build structured prompt
        system_prompt = """You are a document structure analysis expert. Analyze the provided document text and identify its logical structure including headings, paragraphs, lists, tables, and figures.

Return your analysis as a valid JSON object with this exact structure:
{
  "title": "Document title if identifiable",
  "elements": [
    {
      "id": "unique_element_id",
      "type": "heading|paragraph|list|table|figure",
      "page_number": 1,
      "text": "element text content",
      "level": 1-6,
      "confidence": 0.95,
      "children": []
    }
  ],
  "reading_order": ["element_id_1", "element_id_2"],
  "metadata": {
    "total_elements": 10,
    "analysis_confidence": 0.92
  }
}

Key requirements:
- Identify headings by typography, spacing, and semantic context
- Recognize bulleted and numbered lists
- Detect table structures and their content organization
- Identify figures, charts, and images with their captions
- Maintain logical reading order
- Assign realistic confidence scores (0.0-1.0)
- Use semantic analysis, not just formatting cues"""

        user_prompt = f"""Please analyze the following document structure:

{context}

Document Text:
{document_text}

{custom_instructions or ''}

Provide a detailed structural analysis as JSON."""

        return self.invoke_claude(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model_id=ClaudeModel.CLAUDE_3_5_SONNET,
            max_tokens=config.bedrock_max_tokens,
            temperature=0.1,  # Low temperature for consistent structure analysis
        )

    @tracer.capture_method
    def generate_alt_text(
        self,
        figure_context: str,
        document_context: str | None = None,
        figure_type: str | None = None,
        existing_caption: str | None = None,
    ) -> BedrockResponse:
        """Generate alt text for figures using Claude 3.5.

        Args:
            figure_context: Context about the figure from document
            document_context: Broader document context
            figure_type: Type of figure (chart, image, diagram, etc.)
            existing_caption: Existing figure caption if available

        Returns:
            Alt text generation response
        """
        system_prompt = """You are an accessibility expert specializing in creating descriptive alternative text for figures, charts, and images in documents.

Generate concise but descriptive alt text that:
1. Describes the essential information conveyed by the figure
2. Is contextually relevant to the surrounding document
3. Follows WCAG guidelines for alt text
4. Is typically 1-2 sentences, rarely more than 125 characters
5. Focuses on meaning, not just visual elements

Return your response as JSON:
{
  "alt_text": "Descriptive alt text for the figure",
  "description_type": "decorative|informative|complex",
  "confidence": 0.95,
  "reasoning": "Brief explanation of the alt text choice"
}"""

        context_parts = [f"Figure context: {figure_context}"]

        if document_context:
            context_parts.append(f"Document context: {document_context}")

        if figure_type:
            context_parts.append(f"Figure type: {figure_type}")

        if existing_caption:
            context_parts.append(f"Existing caption: {existing_caption}")

        user_prompt = f"""Please generate appropriate alt text for this figure:

{chr(10).join(context_parts)}

Consider the document context and provide alt text that would be most helpful for someone using a screen reader."""

        return self.invoke_claude(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model_id=ClaudeModel.CLAUDE_3_5_SONNET,
            max_tokens=1000,  # Shorter responses for alt text
            temperature=0.2,
        )

    @tracer.capture_method
    def validate_accessibility(
        self,
        document_structure: dict[str, Any],
        content_sample: str,
        validation_criteria: list[str] | None = None,
    ) -> BedrockResponse:
        """Validate document accessibility using Claude 3.5.

        Args:
            document_structure: Document structure analysis
            content_sample: Sample of document content
            validation_criteria: Specific criteria to validate against

        Returns:
            Accessibility validation response
        """
        criteria = validation_criteria or [
            "WCAG 2.1 AA compliance",
            "Proper heading hierarchy",
            "Alt text for images",
            "Reading order",
            "Color contrast considerations",
        ]

        system_prompt = f"""You are an accessibility compliance expert. Analyze the document structure and content for accessibility issues based on {', '.join(criteria)}.

Return your analysis as JSON:
{{
  "overall_score": 85.5,
  "compliance_level": "AA|A|Non-compliant",
  "issues": [
    {{
      "type": "missing_alt_text",
      "severity": "error|warning|info",
      "message": "Description of the issue",
      "location": "Element or page reference",
      "recommendation": "How to fix this issue"
    }}
  ],
  "strengths": ["List of accessibility strengths"],
  "summary": "Brief summary of accessibility status"
}}"""

        user_prompt = f"""Please evaluate this document's accessibility:

Document Structure:
{json.dumps(document_structure, indent=2)}

Content Sample:
{content_sample}

Validation Criteria:
{chr(10).join(f'- {criterion}' for criterion in criteria)}

Provide a comprehensive accessibility assessment."""

        return self.invoke_claude(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model_id=ClaudeModel.CLAUDE_3_5_SONNET,
            max_tokens=config.bedrock_max_tokens,
            temperature=0.1,
        )

    @tracer.capture_method
    def invoke_with_retry(
        self,
        invoke_func: Callable[[], BedrockResponse],
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> BedrockResponse:
        """Invoke Bedrock with automatic retry logic.

        Args:
            invoke_func: Function that performs the Bedrock invocation
            max_retries: Maximum number of retry attempts
            backoff_multiplier: Backoff multiplier for retry delays

        Returns:
            Successful Bedrock response

        Raises:
            BedrockError: If all retries fail
        """
        import time

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return invoke_func()

            except BedrockError as e:
                last_exception = e

                # Don't retry for certain errors
                if "ValidationException" in str(e) or "ModelNotReadyException" in str(
                    e
                ):
                    raise e

                if attempt < max_retries:
                    delay = backoff_multiplier**attempt
                    logger.warning(
                        f"Bedrock invocation failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Bedrock invocation failed after {max_retries + 1} attempts"
                    )
                    raise e

        # This should never be reached, but just in case
        raise last_exception or BedrockError("Unknown error in retry logic")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation).

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: ~4 characters per token for English text
        return len(text) // 4
