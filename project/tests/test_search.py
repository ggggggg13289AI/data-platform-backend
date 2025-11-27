from django.test import TestCase
from project.services.search_registry import ProjectSearchRegistry, SearchResult

class SearchRegistryTest(TestCase):
    def test_registry_decorator(self):
        @ProjectSearchRegistry.register('test_type')
        def mock_provider(pid, q):
            return [SearchResult('test_type', '123', 1.0, 'snippet', {}, '')]
        
        self.assertIn('test_type', ProjectSearchRegistry._providers)
        results = ProjectSearchRegistry.search('pid', 'q')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].resource_type, 'test_type')

