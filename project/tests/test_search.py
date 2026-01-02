from django.test import TestCase

from project.services.search_registry import ProjectSearchRegistry, SearchResult


class SearchRegistryTest(TestCase):
    def tearDown(self):
        ProjectSearchRegistry._providers.clear()

    def _build_result(
        self,
        resource_type: str,
        accession: str,
        score: float,
        timestamp: str,
    ) -> SearchResult:
        return SearchResult(
            resource_type=resource_type,
            accession_number=accession,
            score=score,
            snippet="",
            resource_payload={},
            resource_timestamp=timestamp,
        )

    def test_registry_decorator_registers_provider(self):
        @ProjectSearchRegistry.register("test_type")
        def mock_provider(pid, q, limit: int = 10):
            return [self._build_result("test_type", "123", 1.0, "2025-01-01T00:00:00")]

        self.assertIn("test_type", ProjectSearchRegistry._providers)
        results = ProjectSearchRegistry.search("proj", "term")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].resource_type, "test_type")

    def test_search_filters_requested_resource_types(self):
        @ProjectSearchRegistry.register("study")
        def study_provider(pid, q, limit: int = 5):
            return [self._build_result("study", "S1", 0.5, "2025-01-01T00:00:00")]

        @ProjectSearchRegistry.register("report")
        def report_provider(pid, q, limit: int = 5):
            return [self._build_result("report", "R1", 0.8, "2025-01-02T00:00:00")]

        results = ProjectSearchRegistry.search("proj", "term", resource_types=["report"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].resource_type, "report")

    def test_search_sorting_and_score_normalization(self):
        @ProjectSearchRegistry.register("study")
        def study_provider(pid, q, limit: int = 5):
            return [
                self._build_result("study", "S1", 0.5, "2025-01-01T00:00:00"),
                self._build_result("study", "S2", 1.0, "2025-01-02T00:00:00"),
            ]

        @ProjectSearchRegistry.register("report")
        def report_provider(pid, q, limit: int = 5):
            return [
                self._build_result("report", "R1", 1.5, "2025-01-03T00:00:00"),
                self._build_result("report", "R2", 1.5, "2025-01-01T12:00:00"),
            ]

        results = ProjectSearchRegistry.search("proj", "term")
        # Highest normalized score should be report entries (score -> 1.0)
        self.assertEqual(results[0].resource_type, "report")
        self.assertEqual(results[0].score, 1.0)
        # Tie broken by timestamp (newer first)
        self.assertEqual(results[1].accession_number, "R2")
