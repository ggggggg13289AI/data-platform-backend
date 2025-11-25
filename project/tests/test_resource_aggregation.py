from django.test import TestCase
from project.services.accession_resolver import AccessionKeyResolver

class AccessionResolverTest(TestCase):
    def test_resolve_study(self):
        self.assertEqual(AccessionKeyResolver.resolve_study_id('ACC123'), 'ACC123')

    def test_resolve_report(self):
        self.assertEqual(AccessionKeyResolver.resolve_report_id('ACC123'), 'ACC123')

