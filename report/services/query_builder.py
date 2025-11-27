"""
Advanced query builder for report search DSL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from django.contrib.postgres.search import SearchQuery
from django.db.models import Q


class AdvancedQueryValidationError(Exception):
    """Raised when the advanced search payload is invalid."""


@dataclass
class QueryBuildResult:
    """Represents the parsed boolean filters and full-text search query."""

    filters: Q
    search_query: SearchQuery | None


class AdvancedQueryBuilder:
    """
    Convert JSON DSL payloads into Django Q objects and SearchQuery instances.

    Guardrails:
    - Maximum nesting depth: 5
    - Maximum nodes (groups + conditions): 20
    """

    MAX_DEPTH = 5
    MAX_NODES = 20
    SEARCH_CONFIG = 'simple'

    LOGICAL_OPERATORS = {'AND', 'OR', 'NOT'}

    TEXT_OPERATORS = {'contains', 'not_contains', 'equals', 'not_equals', 'starts_with', 'ends_with'}
    LIST_OPERATORS = {'in', 'not_in'}
    RANGE_OPERATORS = {'between', 'gte', 'lte'}

    # Report field configuration
    REPORT_FIELD_CONFIG: dict[str, dict[str, Any]] = {
        'title': {'field': 'title', 'operators': TEXT_OPERATORS},
        'report_type': {'field': 'report_type', 'operators': TEXT_OPERATORS | LIST_OPERATORS},
        'report_id': {'field': 'report_id', 'operators': TEXT_OPERATORS},
        'uid': {'field': 'uid', 'operators': TEXT_OPERATORS},
        'mod': {'field': 'mod', 'operators': TEXT_OPERATORS},
        'verified_at': {'field': 'verified_at', 'operators': RANGE_OPERATORS},
        'created_at': {'field': 'created_at', 'operators': RANGE_OPERATORS},
        'content': {'field': 'search_vector', 'operators': {'search'}},
    }

    # Study field configuration (cross-model query via subquery)
    STUDY_FIELD_CONFIG: dict[str, dict[str, Any]] = {
        # Patient Info
        'study.patient_name': {'db_field': 'patient_name', 'operators': TEXT_OPERATORS, 'type': 'text'},
        'study.patient_age': {'db_field': 'patient_age', 'operators': RANGE_OPERATORS, 'type': 'integer'},
        'study.patient_gender': {'db_field': 'patient_gender', 'operators': LIST_OPERATORS, 'type': 'choice'},
        
        # Exam Info
        'study.exam_source': {'db_field': 'exam_source', 'operators': TEXT_OPERATORS | LIST_OPERATORS, 'type': 'text'},
        'study.exam_item': {'db_field': 'exam_item', 'operators': TEXT_OPERATORS, 'type': 'text'},
        'study.exam_status': {'db_field': 'exam_status', 'operators': LIST_OPERATORS, 'type': 'choice'},
        'study.equipment_type': {'db_field': 'equipment_type', 'operators': TEXT_OPERATORS | LIST_OPERATORS, 'type': 'text'},
        
        # Time Range
        'study.order_datetime': {'db_field': 'order_datetime', 'operators': RANGE_OPERATORS, 'type': 'datetime'},
        'study.check_in_datetime': {'db_field': 'check_in_datetime', 'operators': RANGE_OPERATORS, 'type': 'datetime'},
        'study.report_certification_datetime': {'db_field': 'report_certification_datetime', 'operators': RANGE_OPERATORS, 'type': 'datetime'},
    }

    # Combined field configuration
    FIELD_CONFIG: dict[str, dict[str, Any]] = {
        **REPORT_FIELD_CONFIG,
        **STUDY_FIELD_CONFIG,
    }

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload or {}
        self._node_count = 0

    def build(self) -> QueryBuildResult:
        """Entrypoint for converting payload to Q / SearchQuery."""
        if not self.payload:
            raise AdvancedQueryValidationError('Query payload is required')

        filters, search_query = self._build_node(self.payload, depth=1)
        return QueryBuildResult(filters=filters or Q(), search_query=search_query)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_node(self, node: Any, depth: int) -> tuple[Q, SearchQuery | None]:
        self._increment_nodes()
        if depth > self.MAX_DEPTH:
            raise AdvancedQueryValidationError(
                f'Max depth ({self.MAX_DEPTH}) exceeded. Simplify the query.'
            )

        if isinstance(node, dict) and 'conditions' in node:
            return self._build_group(node, depth)
        return self._build_condition(node)

    def _build_group(self, node: dict[str, Any], depth: int) -> tuple[Q, SearchQuery | None]:
        operator = (node.get('operator') or 'AND').upper()
        if operator not in self.LOGICAL_OPERATORS:
            raise AdvancedQueryValidationError(f'Unsupported logical operator: {operator}')

        conditions = node.get('conditions')
        if not isinstance(conditions, Iterable):
            raise AdvancedQueryValidationError('Group "conditions" must be a list')

        child_results: list[tuple[Q, SearchQuery | None]] = []
        for child in conditions:
            child_results.append(self._build_node(child, depth + 1))

        if not child_results:
            raise AdvancedQueryValidationError('Groups must contain at least one condition')

        filters = self._combine_filters(child_results, 'AND' if operator == 'NOT' else operator)
        search_query = self._combine_search_queries(
            child_results, 'AND' if operator == 'NOT' else operator
        )

        if operator == 'NOT':
            filters = ~filters
            search_query = ~search_query if search_query is not None else None

        return filters, search_query

    def _build_condition(self, node: Any) -> tuple[Q, SearchQuery | None]:
        if not isinstance(node, dict):
            raise AdvancedQueryValidationError('Condition nodes must be objects')

        field_key = node.get('field')
        operator = (node.get('operator') or 'equals').lower()
        value = node.get('value')

        if not field_key or field_key not in self.FIELD_CONFIG:
            raise AdvancedQueryValidationError(f'Unsupported field: {field_key}')

        # Check if this is a Study field (cross-model query)
        if field_key.startswith('study.'):
            return self._build_study_condition(field_key, operator, value), None

        field_meta = self.FIELD_CONFIG[field_key]
        if operator not in field_meta['operators']:
            allowed = ', '.join(sorted(field_meta['operators']))
            raise AdvancedQueryValidationError(
                f'Operator "{operator}" is not allowed for field "{field_key}". '
                f'Allowed: {allowed}'
            )

        if field_key == 'content':
            return self._build_search_condition(value)

        field_name = field_meta['field']

        if operator in self.TEXT_OPERATORS:
            return self._build_text_condition(field_name, operator, value), None

        if operator in self.LIST_OPERATORS:
            return self._build_list_condition(field_name, operator, value), None

        if operator in self.RANGE_OPERATORS:
            return self._build_range_condition(field_name, operator, value), None

        raise AdvancedQueryValidationError(f'Unhandled operator "{operator}"')

    def _build_text_condition(self, field: str, operator: str, raw_value: Any) -> Q:
        value = self._require_string(raw_value, field)
        lookup_map = {
            'contains': 'icontains',
            'not_contains': 'icontains',
            'equals': 'iexact',
            'not_equals': 'iexact',
            'starts_with': 'istartswith',
            'ends_with': 'iendswith',
        }
        lookup = lookup_map[operator]
        condition = Q(**{f'{field}__{lookup}': value})
        if operator.startswith('not_'):
            return ~condition
        return condition

    def _build_list_condition(self, field: str, operator: str, raw_value: Any) -> Q:
        if not isinstance(raw_value, list) or len(raw_value) == 0:
            raise AdvancedQueryValidationError(f'Field "{field}" expects a non-empty list')

        condition = Q(**{f'{field}__in': raw_value})
        if operator == 'not_in':
            return ~condition
        return condition

    def _build_range_condition(self, field: str, operator: str, raw_value: Any) -> Q:
        if operator == 'between':
            if not isinstance(raw_value, dict):
                raise AdvancedQueryValidationError(f'Field "{field}" expects a range object')
            start = raw_value.get('start')
            end = raw_value.get('end')
            if not start and not end:
                raise AdvancedQueryValidationError(
                    f'Field "{field}" range requires at least one bound'
                )
            query = Q()
            if start:
                query &= Q(**{f'{field}__gte': start})
            if end:
                query &= Q(**{f'{field}__lte': end})
            return query

        value = self._require_string(raw_value, field)
        lookup = 'gte' if operator == 'gte' else 'lte'
        return Q(**{f'{field}__{lookup}': value})

    def _build_study_condition(self, field_key: str, operator: str, value: Any) -> Q:
        """
        Build subquery filter for Study fields.
        
        Uses Q(report_id__in=Study.objects.filter(...).values_list('exam_id', flat=True))
        to maintain performance without ForeignKey relationship.
        """
        from study.models import Study
        
        if field_key not in self.STUDY_FIELD_CONFIG:
            raise AdvancedQueryValidationError(f'Unsupported Study field: {field_key}')
        
        field_meta = self.STUDY_FIELD_CONFIG[field_key]
        db_field = field_meta['db_field']
        
        # Validate operator
        if operator not in field_meta['operators']:
            allowed = ', '.join(sorted(field_meta['operators']))
            raise AdvancedQueryValidationError(
                f'Operator "{operator}" is not allowed for field "{field_key}". '
                f'Allowed: {allowed}'
            )
        
        # Build Study filter based on operator type
        if operator in self.TEXT_OPERATORS:
            study_q = self._build_text_condition(db_field, operator, value)
        elif operator in self.LIST_OPERATORS:
            study_q = self._build_list_condition(db_field, operator, value)
        elif operator in self.RANGE_OPERATORS:
            study_q = self._build_range_condition(db_field, operator, value)
        else:
            raise AdvancedQueryValidationError(
                f'Operator "{operator}" not supported for Study field "{field_key}"'
            )
        
        # Execute subquery to get matching exam_ids
        matching_exam_ids = Study.objects.filter(study_q).values_list('exam_id', flat=True)
        
        # Convert to Report filter
        return Q(report_id__in=matching_exam_ids)

    def _build_search_condition(self, raw_value: Any) -> tuple[Q, SearchQuery]:
        value = self._require_string(raw_value, 'content')
        if not value.strip():
            raise AdvancedQueryValidationError('Full-text search value cannot be empty')
        search_query = SearchQuery(value.strip(), config=self.SEARCH_CONFIG, search_type='plain')
        return Q(), search_query

    @staticmethod
    def _combine_filters(
        results: Iterable[tuple[Q, SearchQuery | None]],
        operator: str,
    ) -> Q:
        combined = Q()
        for filters, _ in results:
            if operator == 'AND':
                combined &= filters
            else:
                combined |= filters
        return combined

    @staticmethod
    def _combine_search_queries(
        results: Iterable[tuple[Q, SearchQuery | None]],
        operator: str,
    ) -> SearchQuery | None:
        queries = [search_query for _, search_query in results if search_query is not None]
        if not queries:
            return None

        combined = queries[0]
        for query in queries[1:]:
            combined = combined & query if operator == 'AND' else combined | query
        return combined

    def _increment_nodes(self) -> None:
        self._node_count += 1
        if self._node_count > self.MAX_NODES:
            raise AdvancedQueryValidationError(
                f'Max conditions ({self.MAX_NODES}) exceeded. Reduce the number of rules.'
            )

    @staticmethod
    def _require_string(raw_value: Any, field: str) -> str:
        if not isinstance(raw_value, str):
            raise AdvancedQueryValidationError(f'Field "{field}" expects a string value')
        trimmed = raw_value.strip()
        if not trimmed:
            raise AdvancedQueryValidationError(f'Field "{field}" cannot be empty')
        return trimmed

