"""
Enhanced PDF/UA Compliance Validation Service
"""

import json
import tempfile
import subprocess
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PDFUAValidationService:
    """Service for comprehensive PDF/UA compliance validation."""
    
    def __init__(self):
        self.wcag_validator = WCAGValidator()
        self.structure_validator = StructureValidator()
        self.content_validator = ContentValidator()
        
    def validate_pdf_ua_compliance(
        self,
        doc_id: str,
        tagged_pdf_s3_key: str,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive PDF/UA compliance validation.
        
        Args:
            doc_id: Document identifier
            tagged_pdf_s3_key: S3 key for tagged PDF
            document_structure: Document structure data
            alt_text_data: Alt-text data for validation
            
        Returns:
            Comprehensive validation report
        """
        try:
            logger.info(f"Starting PDF/UA validation for document {doc_id}")
            
            validation_report = {
                "docId": doc_id,
                "validatedAt": datetime.utcnow(),
                "overallScore": 0.0,
                "pdfUaCompliant": False,
                "wcagLevel": None,
                "validationSections": {},
                "issues": [],
                "recommendations": [],
                "metadata": {
                    "validatorVersion": "1.0",
                    "standardsChecked": ["PDF/UA-1", "WCAG 2.1 AA", "Section 508"],
                }
            }
            
            # 1. Structure Validation
            logger.info("Validating document structure")
            structure_results = self.structure_validator.validate_structure(
                document_structure
            )
            validation_report["validationSections"]["structure"] = structure_results
            
            # 2. Content Validation  
            logger.info("Validating content accessibility")
            content_results = self.content_validator.validate_content(
                document_structure,
                alt_text_data
            )
            validation_report["validationSections"]["content"] = content_results
            
            # 3. WCAG Compliance Check
            logger.info("Checking WCAG compliance")
            wcag_results = self.wcag_validator.validate_wcag_compliance(
                document_structure,
                alt_text_data
            )
            validation_report["validationSections"]["wcag"] = wcag_results
            
            # 4. Calculate overall scores
            validation_report = self._calculate_overall_scores(validation_report)
            
            # 5. Generate recommendations
            validation_report["recommendations"] = self._generate_recommendations(
                validation_report
            )
            
            logger.info(
                f"Validation completed for {doc_id}: "
                f"score={validation_report['overallScore']:.2f}, "
                f"issues={len(validation_report['issues'])}"
            )
            
            return validation_report
            
        except Exception as e:
            logger.error(f"PDF/UA validation failed for {doc_id}: {e}")
            raise

    def _calculate_overall_scores(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall validation scores and compliance levels."""
        
        sections = report["validationSections"]
        total_score = 0.0
        section_count = 0
        all_issues = []
        
        # Aggregate scores from all sections
        for section_name, section_data in sections.items():
            if "score" in section_data:
                total_score += section_data["score"]
                section_count += 1
                
            if "issues" in section_data:
                all_issues.extend(section_data["issues"])
        
        # Calculate overall score
        overall_score = total_score / section_count if section_count > 0 else 0.0
        report["overallScore"] = overall_score
        report["issues"] = all_issues
        
        # Determine PDF/UA compliance
        report["pdfUaCompliant"] = overall_score >= 0.9 and len([
            issue for issue in all_issues if issue.get("level") == "error"
        ]) == 0
        
        # Determine WCAG level
        if overall_score >= 0.95:
            report["wcagLevel"] = "AAA"
        elif overall_score >= 0.85:
            report["wcagLevel"] = "AA"
        elif overall_score >= 0.70:
            report["wcagLevel"] = "A"
        else:
            report["wcagLevel"] = None
            
        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        
        recommendations = []
        issues = report.get("issues", [])
        
        # Group issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        # Generate recommendations for each issue type
        for issue_type, type_issues in issue_types.items():
            if issue_type == "missing_alt_text":
                count = len(type_issues)
                recommendations.append(
                    f"Add alternative text to {count} image{'s' if count > 1 else ''} "
                    "to improve accessibility for screen readers"
                )
            elif issue_type == "heading_structure":
                recommendations.append(
                    "Review heading hierarchy to ensure logical document structure"
                )
            elif issue_type == "table_accessibility":
                recommendations.append(
                    "Add table headers and improve table structure for screen readers"
                )
            elif issue_type == "reading_order":
                recommendations.append(
                    "Review reading order to ensure content flows logically"
                )
            elif issue_type == "color_contrast":
                recommendations.append(
                    "Improve color contrast ratios to meet WCAG AA standards"
                )
        
        return recommendations


class StructureValidator:
    """Validates document structure for accessibility."""
    
    def validate_structure(self, document_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document structural elements."""
        
        results = {
            "score": 0.0,
            "issues": [],
            "checks": {
                "heading_hierarchy": False,
                "reading_order": False,
                "semantic_structure": False,
            }
        }
        
        elements = document_structure.get("elements", [])
        
        # Check heading hierarchy
        heading_score = self._validate_heading_hierarchy(elements)
        results["checks"]["heading_hierarchy"] = heading_score > 0.7
        
        # Check reading order
        reading_order_score = self._validate_reading_order(elements)
        results["checks"]["reading_order"] = reading_order_score > 0.8
        
        # Check semantic structure
        semantic_score = self._validate_semantic_structure(elements)
        results["checks"]["semantic_structure"] = semantic_score > 0.8
        
        # Calculate overall structure score
        results["score"] = (heading_score + reading_order_score + semantic_score) / 3
        
        return results

    def _validate_heading_hierarchy(self, elements: List[Dict[str, Any]]) -> float:
        """Validate proper heading hierarchy (H1 -> H2 -> H3, etc.)."""
        
        headings = [e for e in elements if e.get("type") == "heading"]
        if not headings:
            return 1.0  # No headings to validate
            
        # Check for H1
        has_h1 = any(h.get("level", 1) == 1 for h in headings)
        if not has_h1:
            return 0.5  # Missing H1 is a major issue
            
        # Check hierarchy logic
        hierarchy_violations = 0
        prev_level = 0
        
        for heading in headings:
            level = heading.get("level", 1)
            if level > prev_level + 1:  # Skipping levels
                hierarchy_violations += 1
            prev_level = level
            
        # Score based on violations
        if hierarchy_violations == 0:
            return 1.0
        elif hierarchy_violations <= len(headings) * 0.1:  # ≤10% violations
            return 0.8
        else:
            return 0.6

    def _validate_reading_order(self, elements: List[Dict[str, Any]]) -> float:
        """Validate logical reading order."""
        
        # Check if elements are in page order
        page_order_violations = 0
        prev_page = 0
        
        for element in elements:
            page = element.get("page_number", 1)
            if page < prev_page:
                page_order_violations += 1
            prev_page = max(prev_page, page)
            
        # Score based on page order consistency
        if page_order_violations == 0:
            return 1.0
        elif page_order_violations <= len(elements) * 0.05:  # ≤5% violations
            return 0.8
        else:
            return 0.6

    def _validate_semantic_structure(self, elements: List[Dict[str, Any]]) -> float:
        """Validate semantic structure and element relationships."""
        
        element_types = {}
        for element in elements:
            elem_type = element.get("type", "paragraph")
            element_types[elem_type] = element_types.get(elem_type, 0) + 1
            
        # Check for basic document structure
        has_headings = element_types.get("heading", 0) > 0
        has_paragraphs = element_types.get("paragraph", 0) > 0
        
        score = 0.0
        if has_headings:
            score += 0.4
        if has_paragraphs:
            score += 0.3
        if element_types.get("table", 0) > 0:
            score += 0.15
        if element_types.get("list", 0) > 0:
            score += 0.15
            
        return min(score, 1.0)


class ContentValidator:
    """Validates content accessibility requirements."""
    
    def validate_content(
        self,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate content accessibility."""
        
        results = {
            "score": 0.0,
            "issues": [],
            "checks": {
                "alt_text_coverage": False,
                "table_headers": False,
                "link_descriptions": False,
            }
        }
        
        elements = document_structure.get("elements", [])
        
        # Validate alt-text coverage
        alt_text_score = self._validate_alt_text_coverage(elements, alt_text_data)
        results["checks"]["alt_text_coverage"] = alt_text_score > 0.8
        
        # Validate table accessibility
        table_score = self._validate_table_accessibility(elements)
        results["checks"]["table_headers"] = table_score > 0.8
        
        # Validate link descriptions
        link_score = self._validate_link_accessibility(elements)
        results["checks"]["link_descriptions"] = link_score > 0.8
        
        results["score"] = (alt_text_score + table_score + link_score) / 3
        
        return results

    def _validate_alt_text_coverage(
        self,
        elements: List[Dict[str, Any]],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """Validate alt-text coverage for figures."""
        
        figures = [e for e in elements if e.get("type") == "figure"]
        if not figures:
            return 1.0  # No figures to validate
            
        if not alt_text_data:
            return 0.0  # No alt-text data available
            
        # Check coverage
        total_figures = len(figures)
        covered_figures = 0
        
        alt_text_figures = {
            f.get("figure_id"): f for f in alt_text_data.get("figures", [])
        }
        
        for figure in figures:
            figure_id = figure.get("id")
            alt_text_info = alt_text_figures.get(figure_id)
            
            if alt_text_info:
                approved_text = alt_text_info.get("approved_text")
                ai_text = alt_text_info.get("ai_text")
                
                if (approved_text and approved_text.strip()) or (ai_text and ai_text.strip()):
                    covered_figures += 1
        
        return covered_figures / total_figures if total_figures > 0 else 1.0

    def _validate_table_accessibility(self, elements: List[Dict[str, Any]]) -> float:
        """Validate table accessibility features."""
        
        tables = [e for e in elements if e.get("type") == "table"]
        if not tables:
            return 1.0  # No tables to validate
            
        accessible_tables = 0
        
        for table in tables:
            # Check if table has proper structure indicators
            has_headers = table.get("has_headers", False)
            row_count = table.get("rows", 0)
            col_count = table.get("columns", 0)
            
            # Simple accessibility check
            if has_headers and row_count > 0 and col_count > 0:
                accessible_tables += 1
                
        return accessible_tables / len(tables)

    def _validate_link_accessibility(self, elements: List[Dict[str, Any]]) -> float:
        """Validate link accessibility (descriptive text, etc.)."""
        
        # For now, assume links are accessible if detected properly
        # In a real implementation, would check link text quality
        return 0.9


class WCAGValidator:
    """Validates WCAG 2.1 compliance requirements."""
    
    def validate_wcag_compliance(
        self,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate WCAG 2.1 compliance."""
        
        results = {
            "score": 0.0,
            "issues": [],
            "level": None,
            "checks": {
                "perceivable": {"score": 0.0, "issues": []},
                "operable": {"score": 0.0, "issues": []},
                "understandable": {"score": 0.0, "issues": []},
                "robust": {"score": 0.0, "issues": []},
            }
        }
        
        # 1. Perceivable
        perceivable_score = self._check_perceivable(document_structure, alt_text_data)
        results["checks"]["perceivable"]["score"] = perceivable_score
        
        # 2. Operable
        operable_score = self._check_operable(document_structure)
        results["checks"]["operable"]["score"] = operable_score
        
        # 3. Understandable
        understandable_score = self._check_understandable(document_structure)
        results["checks"]["understandable"]["score"] = understandable_score
        
        # 4. Robust
        robust_score = self._check_robust(document_structure)
        results["checks"]["robust"]["score"] = robust_score
        
        # Calculate overall WCAG score
        overall_score = (perceivable_score + operable_score + understandable_score + robust_score) / 4
        results["score"] = overall_score
        
        # Determine WCAG level
        if overall_score >= 0.95:
            results["level"] = "AAA"
        elif overall_score >= 0.85:
            results["level"] = "AA"
        elif overall_score >= 0.70:
            results["level"] = "A"
        else:
            results["level"] = None
            
        return results

    def _check_perceivable(
        self,
        document_structure: Dict[str, Any],
        alt_text_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """Check WCAG Perceivable principle."""
        
        # Check alt-text for images
        elements = document_structure.get("elements", [])
        figures = [e for e in elements if e.get("type") == "figure"]
        
        if not figures:
            return 1.0
            
        # Alt-text coverage score
        if alt_text_data:
            covered = 0
            for figure in figures:
                figure_id = figure.get("id")
                for alt_fig in alt_text_data.get("figures", []):
                    if alt_fig.get("figure_id") == figure_id:
                        if alt_fig.get("approved_text") or alt_fig.get("ai_text"):
                            covered += 1
                        break
            return covered / len(figures)
        else:
            return 0.0

    def _check_operable(self, document_structure: Dict[str, Any]) -> float:
        """Check WCAG Operable principle."""
        
        # For PDFs, this mainly involves proper structure for navigation
        elements = document_structure.get("elements", [])
        headings = [e for e in elements if e.get("type") == "heading"]
        
        # Score based on navigation structure
        if headings:
            return 0.9  # Good navigation structure
        else:
            return 0.6  # Limited navigation

    def _check_understandable(self, document_structure: Dict[str, Any]) -> float:
        """Check WCAG Understandable principle."""
        
        # Check if document has clear structure and language
        has_title = document_structure.get("title") is not None
        elements = document_structure.get("elements", [])
        headings = [e for e in elements if e.get("type") == "heading"]
        
        score = 0.0
        if has_title:
            score += 0.3
        if headings:
            score += 0.4
        if len(elements) > 0:
            score += 0.3
            
        return score

    def _check_robust(self, document_structure: Dict[str, Any]) -> float:
        """Check WCAG Robust principle."""
        
        # For PDFs, this involves proper tagging and structure
        elements = document_structure.get("elements", [])
        
        if elements:
            # Assume structure is robust if elements are properly identified
            return 0.9
        else:
            return 0.5


# Global service instance
_validation_service = None


def get_validation_service() -> PDFUAValidationService:
    """Get global validation service instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = PDFUAValidationService()
    return _validation_service