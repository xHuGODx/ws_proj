import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_returns_ok(self):
        response = self.client.get(reverse("championship:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Formula 1 Data Explorer")


class FakeGraphDBClient:
    constructors = {
        "1": {"label": "McLaren"},
        "2": {"label": "Ferrari"},
    }
    drivers = {}

    def query(self, sparql: str) -> list[dict[str, str]]:
        normalized = " ".join(sparql.split())

        if "SELECT (MAX(?id) AS ?maxId)" in normalized:
            max_id = max((int(driver_id) for driver_id in self.drivers), default=0)
            return [{"maxId": str(max_id)}]

        if "SELECT ?constructorId ?label WHERE" in normalized:
            return [
                {"constructorId": constructor_id, "label": data["label"]}
                for constructor_id, data in sorted(self.constructors.items(), key=lambda item: item[1]["label"])
            ]

        if "SELECT ?forename ?surname ?code ?number ?dob ?nationality ?constructorId ?url WHERE" in normalized:
            driver_id = self._extract_entity_id(normalized, "driver")
            driver = self.drivers.get(driver_id)
            if not driver:
                return []
            row = {
                "forename": driver["forename"],
                "surname": driver["surname"],
                "code": driver.get("code", ""),
                "number": driver.get("number", ""),
                "dob": driver.get("dob", ""),
                "nationality": driver.get("nationality", ""),
                "url": driver.get("url", ""),
            }
            if driver.get("constructor_id"):
                row["constructorId"] = driver["constructor_id"]
            return [row]

        if "SELECT ?label WHERE" in normalized and "rdfs:label ?label" in normalized:
            driver_id = self._extract_entity_id(normalized, "driver")
            driver = self.drivers.get(driver_id)
            if not driver:
                return []
            return [{"label": f'{driver["forename"]} {driver["surname"]}'}]

        return []

    def run_update(self, update_query: str) -> None:
        driver_match = re.search(r"<http://example\.org/resource/driver/(\d+)>", update_query)
        if not driver_match:
            return

        driver_id = driver_match.group(1)
        constructor_match = re.search(r"f1:constructor <http://example\.org/resource/constructor/([^>]+)>", update_query)
        self.drivers[driver_id] = {
            "forename": self._capture(update_query, r'f1:forename "([^"]*)"'),
            "surname": self._capture(update_query, r'f1:surname\s+"([^"]*)"'),
            "code": self._capture(update_query, r'f1:code "([^"]*)"'),
            "number": self._capture(update_query, r"f1:number ([0-9]+)"),
            "dob": self._capture(update_query, r'f1:dob "([^"]+)"\^\^xsd:date'),
            "nationality": self._capture(update_query, r'f1:nationality "([^"]*)"'),
            "url": self._capture(update_query, r"rdfs:seeAlso <([^>]+)>"),
            "constructor_id": constructor_match.group(1) if constructor_match else "",
        }

    @staticmethod
    def _extract_entity_id(sparql: str, kind: str) -> str:
        match = re.search(rf"<http://example\.org/resource/{kind}/([^>]+)>", sparql)
        return match.group(1) if match else ""

    @staticmethod
    def _capture(text: str, pattern: str) -> str:
        match = re.search(pattern, text)
        return match.group(1) if match else ""


@patch("championship.admin_views.GraphDBClient", new=FakeGraphDBClient)
class DriverAdminRelationTests(TestCase):
    def setUp(self):
        super().setUp()
        FakeGraphDBClient.drivers = {
            "7": {
                "forename": "Lando",
                "surname": "Norris",
                "code": "NOR",
                "number": "4",
                "dob": "1999-11-13",
                "nationality": "British",
                "url": "https://example.com/lando",
                "constructor_id": "1",
            }
        }
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secret",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_admin_driver_add_persists_constructor_relation(self):
        response = self.client.post(reverse("championship:admin_driver_add"), {
            "forename": "Oscar",
            "surname": "Piastri",
            "constructor_id": "1",
            "code": "PIA",
            "number": "81",
            "dob": "2001-04-06",
            "nationality": "Australian",
            "url": "https://example.com/oscar",
        })

        self.assertRedirects(response, reverse("championship:admin_drivers"))
        self.assertEqual(FakeGraphDBClient.drivers["8"]["constructor_id"], "1")

    def test_admin_driver_edit_updates_constructor_relation_and_reload(self):
        post_response = self.client.post(reverse("championship:admin_driver_edit", args=["7"]), {
            "forename": "Lando",
            "surname": "Norris",
            "constructor_id": "2",
            "code": "NOR",
            "number": "4",
            "dob": "1999-11-13",
            "nationality": "British",
            "url": "https://example.com/lando",
        })

        self.assertRedirects(post_response, reverse("championship:admin_drivers"))
        self.assertEqual(FakeGraphDBClient.drivers["7"]["constructor_id"], "2")

        get_response = self.client.get(reverse("championship:admin_driver_edit", args=["7"]))

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.context["form"]["constructor_id"].value(), "2")

    def test_admin_driver_edit_can_clear_constructor_relation(self):
        response = self.client.post(reverse("championship:admin_driver_edit", args=["7"]), {
            "forename": "Lando",
            "surname": "Norris",
            "constructor_id": "",
            "code": "NOR",
            "number": "4",
            "dob": "1999-11-13",
            "nationality": "British",
            "url": "https://example.com/lando",
        })

        self.assertRedirects(response, reverse("championship:admin_drivers"))
        self.assertEqual(FakeGraphDBClient.drivers["7"]["constructor_id"], "")

        reload_response = self.client.get(reverse("championship:admin_driver_edit", args=["7"]))

        self.assertEqual(reload_response.context["form"]["constructor_id"].value(), "")
