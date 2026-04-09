"""
Integration tests for multi-question structured Q1/Q2/Q3 flow.

Covers two code paths that together prove structured answers are produced
and stored as a DICT with separate Q1/Q2/Q3 keys — not as a single-line
string — and that the resource aggregator can filter by those keys.

Test 1: `BatchAnalysisService._parse_llm_response` in multi-question mode
        returns a dict[str, str] with one entry per question key.

Test 2: `ResourceAggregator.get_project_resources` with `answers_filter={Q1: no}`
        correctly narrows results to only resources whose annotation
        `metadata["structured_answers"]["Q1"] == "no"`.

Uses SimpleTestCase + unittest.mock to avoid the test-DB migration problem
(common/project apps have no migrations so Django test runner fails to
create test DB tables that depend on auth_user).
"""

import json
from datetime import datetime

from django.test import SimpleTestCase

from ai.services.batch_analysis_service import BatchAnalysisService
from project.schemas import (
    AIAnnotationSummary,
    ProjectResourceAssignment,
    ProjectResourceItem,
    UserInfo,
)
from project.services.resource_aggregator import ResourceAggregator

AD_GUIDELINE_QUESTIONS = [
    {
        "key": "Q1",
        "label": "Does the report mention any aortic dissection (AD) or IMH?",
        "options": ["yes", "no"],
        "depends_on": None,
    },
    {
        "key": "Q2",
        "label": "Has the patient already undergone surgery for the dissection?",
        "options": ["yes", "no", "N/A"],
        "depends_on": {"question_key": "Q1", "expected_value": "yes"},
    },
    {
        "key": "Q3",
        "label": "Stanford classification of the untreated dissection",
        "options": ["type A", "type B", "N/A"],
        "depends_on": {"question_key": "Q2", "expected_value": "no"},
    },
]


class MultiQuestionParseTests(SimpleTestCase):
    """Test 1: LLM JSON → structured_answers dict (not a one-line string)."""

    def test_parse_multi_question_returns_dict_not_string(self):
        """The parser must return a dict[str, str] with separate Q1/Q2/Q3 keys."""
        llm_json = json.dumps(
            {
                "answers": {"Q1": "yes", "Q2": "no", "Q3": "type B"},
                "confidence": 0.93,
                "reasoning": "intimal flap in descending aorta, no surgical markers",
            }
        )

        primary, confidence, structured_answers = BatchAnalysisService._parse_llm_response(
            response=llm_json,
            categories=["AD(+)", "AD(-)", "IMH", "uncertain"],
            questions=AD_GUIDELINE_QUESTIONS,
        )

        # Structured answers must be a dict, NOT a string
        self.assertIsInstance(structured_answers, dict)
        self.assertNotIsInstance(structured_answers, str)

        # Each Q key is stored separately and preserves option casing
        self.assertEqual(set(structured_answers.keys()), {"Q1", "Q2", "Q3"})
        self.assertEqual(structured_answers["Q1"], "yes")
        self.assertEqual(structured_answers["Q2"], "no")
        self.assertEqual(structured_answers["Q3"], "type B")

        # Primary classification derives from the first question (Q1)
        self.assertEqual(primary, "yes")
        self.assertAlmostEqual(confidence, 0.93, places=2)

    def test_parse_multi_question_preserves_na_for_skipped_questions(self):
        """When Q1=no, Q2 and Q3 should be N/A (dict entries, not missing)."""
        llm_json = json.dumps(
            {
                "answers": {"Q1": "no", "Q2": "N/A", "Q3": "N/A"},
                "confidence": 0.99,
                "reasoning": "no dissection or IMH mentioned",
            }
        )

        _, _, structured_answers = BatchAnalysisService._parse_llm_response(
            response=llm_json,
            categories=["AD(+)", "AD(-)", "IMH", "uncertain"],
            questions=AD_GUIDELINE_QUESTIONS,
        )

        self.assertEqual(structured_answers["Q1"], "no")
        self.assertEqual(structured_answers["Q2"], "N/A")
        self.assertEqual(structured_answers["Q3"], "N/A")


def _make_item(accession: str, q1: str, q2: str = "N/A", q3: str = "N/A") -> ProjectResourceItem:
    """Build a ProjectResourceItem whose annotation has structured_answers."""
    return ProjectResourceItem(
        resource_type="report",
        accession_number=accession,
        resource_timestamp=datetime(2026, 1, 1),
        annotation=AIAnnotationSummary(
            id=f"ann-{accession}",
            classification=q1,  # primary classification == Q1 answer
            confidence_score=0.95,
            guideline_name="Test AD guideline",
            guideline_version=1,
            structured_answers={"Q1": q1, "Q2": q2, "Q3": q3},
            created_at=datetime(2026, 1, 1),
        ),
        assignment=ProjectResourceAssignment(
            assigned_at=datetime(2026, 1, 1),
            assigned_by=UserInfo(id="1", name="test", email="t@e.com"),
        ),
    )


class ResourceAggregatorAnswersFilterTests(SimpleTestCase):
    """Test 2: `ResourceAggregator._apply_ai_filters` narrows by structured Q&A.

    Exercises the real filter code path (same classmethod called by
    `get_project_resources`) without touching the DB.
    """

    def setUp(self):
        self.items = [
            _make_item("A001", q1="yes", q2="no", q3="type B"),
            _make_item("A002", q1="no"),
            _make_item("A003", q1="no"),
        ]

    def test_unfiltered_returns_all_three(self):
        # No filter args → identity
        result = ResourceAggregator._apply_ai_filters(self.items)
        self.assertEqual(len(result), 3)

    def test_answers_filter_q1_yes_returns_only_matching(self):
        result = ResourceAggregator._apply_ai_filters(self.items, answers_filter={"Q1": "yes"})
        self.assertEqual(len(result), 1)
        ann = result[0].annotation
        self.assertEqual(ann.structured_answers["Q1"], "yes")
        self.assertEqual(ann.structured_answers["Q3"], "type B")
        # Confirm structured_answers is still a dict, not a flattened string
        self.assertIsInstance(ann.structured_answers, dict)

    def test_answers_filter_q1_no_returns_two(self):
        result = ResourceAggregator._apply_ai_filters(self.items, answers_filter={"Q1": "no"})
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(item.annotation.structured_answers["Q1"], "no")

    def test_answers_filter_multi_key_intersection(self):
        """Q1=yes AND Q3=type B → should match the 1 AD+ case."""
        result = ResourceAggregator._apply_ai_filters(
            self.items, answers_filter={"Q1": "yes", "Q3": "type B"}
        )
        self.assertEqual(len(result), 1)

    def test_answers_filter_case_insensitive(self):
        """Filter matches regardless of upper/lower case."""
        result = ResourceAggregator._apply_ai_filters(self.items, answers_filter={"Q1": "YES"})
        self.assertEqual(len(result), 1)

    def test_confidence_min_filter(self):
        low_conf_item = _make_item("A004", q1="yes")
        low_conf_item.annotation.confidence_score = 0.3
        items = [*self.items, low_conf_item]
        result = ResourceAggregator._apply_ai_filters(items, confidence_min=0.5)
        self.assertEqual(len(result), 3)  # excludes A004 only
        accessions = {item.accession_number for item in result}
        self.assertNotIn("A004", accessions)
