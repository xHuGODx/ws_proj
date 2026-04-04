from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_returns_ok(self):
        response = self.client.get(reverse("championship:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Formula 1 Knowledge Graph")


# Create your tests here.
