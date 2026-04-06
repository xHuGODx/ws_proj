from django.shortcuts import render

from .services.graphdb import GraphDBClient

_COMING_SOON = "championship/coming_soon.html"


def home(request):
    graphdb = GraphDBClient()
    stats = [
        {"value": "75",   "label": "Seasons"},
        {"value": "77",   "label": "Circuits"},
        {"value": "861",  "label": "Drivers"},
        {"value": "212",  "label": "Constructors"},
        {"value": "1125", "label": "Races"},
    ]
    context = {
        "graphdb": graphdb.healthcheck(),
        "stats": stats,
    }
    return render(request, "championship/home.html", context)


def drivers(request):
    return render(request, _COMING_SOON, {"page": "Drivers"})


def constructors(request):
    return render(request, _COMING_SOON, {"page": "Constructors"})


def seasons(request):
    return render(request, _COMING_SOON, {"page": "Seasons"})


def races(request):
    return render(request, _COMING_SOON, {"page": "Races"})


def circuits(request):
    return render(request, _COMING_SOON, {"page": "Circuits"})


def sparql(request):
    return render(request, _COMING_SOON, {"page": "SPARQL"})
