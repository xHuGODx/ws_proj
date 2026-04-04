from django.shortcuts import render

from .services.graphdb import GraphDBClient


def home(request):
    graphdb = GraphDBClient()
    context = {
        "project_title": "Formula 1 Knowledge Graph",
        "graphdb": graphdb.healthcheck(),
        "sections": [
            "Seasons and races",
            "Drivers and constructors",
            "Results and standings",
            "SPARQL query and update operations",
        ],
    }
    return render(request, "championship/home.html", context)
