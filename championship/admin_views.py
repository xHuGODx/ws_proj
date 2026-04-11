from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import (
    CircuitForm,
    ConstructorForm,
    DriverForm,
    LoginForm,
    RaceForm,
    SeasonForm,
)
from .services.graphdb import GraphDBClient

RESOURCE_BASE = "http://example.org/resource/"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sq(value) -> str:
    """Escape a value for embedding in a SPARQL string literal."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _uri(kind: str, entity_id) -> str:
    return f"<{RESOURCE_BASE}{kind}/{entity_id}>"


def _next_id(db: GraphDBClient, id_prop: str) -> int:
    rows = db.query(f"SELECT (MAX(?id) AS ?maxId) WHERE {{ ?e f1:{id_prop} ?id }}")
    try:
        return int(rows[0]["maxId"]) + 1
    except (IndexError, KeyError, ValueError):
        return 1


def _slug(text: str) -> str:
    """Derive a simple ref/slug from a name."""
    import re
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# ── Auth ──────────────────────────────────────────────────────────────────────

def admin_login(request):
    if request.user.is_authenticated:
        return redirect("championship:admin_dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None and user.is_staff:
            login(request, user)
            return redirect(request.GET.get("next", "championship:admin_dashboard"))
        form.add_error(None, "Invalid credentials or insufficient permissions.")
    return render(request, "admin/login.html", {"form": form})


def admin_logout(request):
    logout(request)
    return redirect("championship:admin_login")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required(login_url="championship:admin_login")
def admin_dashboard(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT
          (COUNT(DISTINCT ?driver)      AS ?drivers)
          (COUNT(DISTINCT ?constructor) AS ?constructors)
          (COUNT(DISTINCT ?circuit)     AS ?circuits)
          (COUNT(DISTINCT ?race)        AS ?races)
          (COUNT(DISTINCT ?season)      AS ?seasons)
        WHERE {
          ?race f1:round ?round ; f1:year ?season ; f1:circuit ?circuit .
          ?res  f1:resultId ?anyId ; f1:race ?race ;
                f1:driver ?driver ; f1:constructor ?constructor .
        }
    """)
    counts = rows[0] if rows else {}
    stats = [
        {"label": "Drivers",      "value": counts.get("drivers",      "—"), "url": "admin_drivers"},
        {"label": "Constructors", "value": counts.get("constructors", "—"), "url": "admin_constructors"},
        {"label": "Circuits",     "value": counts.get("circuits",     "—"), "url": "admin_circuits"},
        {"label": "Races",        "value": counts.get("races",        "—"), "url": "admin_races"},
        {"label": "Seasons",      "value": counts.get("seasons",      "—"), "url": "admin_seasons"},
    ]
    return render(request, "admin/dashboard.html", {"stats": stats})


# ── Drivers ───────────────────────────────────────────────────────────────────

@login_required(login_url="championship:admin_login")
def admin_drivers(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT ?driverId ?label ?nationality ?dob ?code WHERE {
          ?d f1:driverId ?driverId ;
             rdfs:label   ?label .
          OPTIONAL { ?d f1:nationality ?nationality }
          OPTIONAL { ?d f1:dob         ?dob }
          OPTIONAL { ?d f1:code        ?code }
        }
        ORDER BY ?label
    """)
    return render(request, "admin/drivers_list.html", {"drivers": rows})


@login_required(login_url="championship:admin_login")
def admin_driver_add(request):
    form = DriverForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        db = GraphDBClient()
        d  = form.cleaned_data
        new_id   = _next_id(db, "driverId")
        ref      = _slug(f"{d['forename']}_{d['surname']}")
        label    = f"{d['forename']} {d['surname']}"
        uri      = _uri("driver", new_id)

        triples = [f'{uri} rdfs:label "{_sq(label)}"',
                   f'f1:driverId {new_id}',
                   f'f1:driverRef "{_sq(ref)}"',
                   f'f1:forename "{_sq(d["forename"])}"',
                   f'f1:surname  "{_sq(d["surname"])}"']
        if d.get("code"):
            triples.append(f'f1:code "{_sq(d["code"]).upper()}"')
        if d.get("number"):
            triples.append(f'f1:number {d["number"]}')
        if d.get("dob"):
            triples.append(f'f1:dob "{d["dob"]}"^^xsd:date')
        if d.get("nationality"):
            triples.append(f'f1:nationality "{_sq(d["nationality"])}"')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"INSERT DATA {{ {body} }}")
        messages.success(request, f'Driver "{label}" added successfully.')
        return redirect("championship:admin_drivers")

    return render(request, "admin/driver_form.html", {"form": form, "action": "Add"})


@login_required(login_url="championship:admin_login")
def admin_driver_edit(request, driver_id: str):
    db  = GraphDBClient()
    uri = _uri("driver", driver_id)

    # Load existing values
    rows = db.query(f"""
        SELECT ?forename ?surname ?code ?number ?dob ?nationality ?url WHERE {{
          {uri} f1:driverId ?anyId .
          OPTIONAL {{ {uri} f1:forename   ?forename   }}
          OPTIONAL {{ {uri} f1:surname    ?surname    }}
          OPTIONAL {{ {uri} f1:code       ?code       }}
          OPTIONAL {{ {uri} f1:number     ?number     }}
          OPTIONAL {{ {uri} f1:dob        ?dob        }}
          OPTIONAL {{ {uri} f1:nationality ?nationality }}
          OPTIONAL {{ {uri} rdfs:seeAlso  ?url        }}
        }} LIMIT 1
    """)
    if not rows:
        messages.error(request, "Driver not found.")
        return redirect("championship:admin_drivers")

    existing = rows[0]
    initial = {
        "forename":    existing.get("forename", ""),
        "surname":     existing.get("surname",  ""),
        "code":        existing.get("code",     ""),
        "number":      existing.get("number",   ""),
        "dob":         existing.get("dob",      ""),
        "nationality": existing.get("nationality", ""),
        "url":         existing.get("url",      ""),
    }

    form = DriverForm(request.POST or initial)

    if request.method == "POST" and form.is_valid():
        d     = form.cleaned_data
        label = f"{d['forename']} {d['surname']}"
        ref   = _slug(f"{d['forename']}_{d['surname']}")

        triples = [f'{uri} rdfs:label "{_sq(label)}"',
                   f'f1:driverId {driver_id}',
                   f'f1:driverRef "{_sq(ref)}"',
                   f'f1:forename "{_sq(d["forename"])}"',
                   f'f1:surname  "{_sq(d["surname"])}"']
        if d.get("code"):
            triples.append(f'f1:code "{_sq(d["code"]).upper()}"')
        if d.get("number"):
            triples.append(f'f1:number {d["number"]}')
        if d.get("dob"):
            triples.append(f'f1:dob "{d["dob"]}"^^xsd:date')
        if d.get("nationality"):
            triples.append(f'f1:nationality "{_sq(d["nationality"])}"')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"""
            DELETE WHERE {{ {uri} ?p ?o }} ;
            INSERT DATA {{ {body} }}
        """)
        messages.success(request, f'Driver "{label}" updated.')
        return redirect("championship:admin_drivers")

    return render(request, "admin/driver_form.html", {
        "form": form, "action": "Edit", "driver_id": driver_id,
        "label": f"{existing.get('forename','')} {existing.get('surname','')}",
    })


@login_required(login_url="championship:admin_login")
def admin_driver_delete(request, driver_id: str):
    if request.method == "POST":
        db  = GraphDBClient()
        uri = _uri("driver", driver_id)
        rows = db.query(f"SELECT ?label WHERE {{ {uri} rdfs:label ?label }} LIMIT 1")
        label = rows[0]["label"] if rows else driver_id
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }}")
        messages.success(request, f'Driver "{label}" deleted.')
    return redirect("championship:admin_drivers")


# ── Constructors ──────────────────────────────────────────────────────────────

@login_required(login_url="championship:admin_login")
def admin_constructors(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT ?constructorId ?label ?nationality WHERE {
          ?c f1:constructorId ?constructorId ;
             rdfs:label        ?label .
          OPTIONAL { ?c f1:nationality ?nationality }
        }
        ORDER BY ?label
    """)
    return render(request, "admin/constructors_list.html", {"constructors": rows})


@login_required(login_url="championship:admin_login")
def admin_constructor_add(request):
    form = ConstructorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        db = GraphDBClient()
        d  = form.cleaned_data
        new_id = _next_id(db, "constructorId")
        ref    = _slug(d["name"])
        uri    = _uri("constructor", new_id)

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:constructorId {new_id}',
                   f'f1:constructorRef "{_sq(ref)}"',
                   f'f1:name "{_sq(d["name"])}"']
        if d.get("nationality"):
            triples.append(f'f1:nationality "{_sq(d["nationality"])}"')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"INSERT DATA {{ {body} }}")
        messages.success(request, f'Constructor "{d["name"]}" added.')
        return redirect("championship:admin_constructors")

    return render(request, "admin/constructor_form.html", {"form": form, "action": "Add"})


@login_required(login_url="championship:admin_login")
def admin_constructor_edit(request, constructor_id: str):
    db  = GraphDBClient()
    uri = _uri("constructor", constructor_id)

    rows = db.query(f"""
        SELECT ?name ?nationality ?url WHERE {{
          {uri} f1:constructorId ?anyId .
          OPTIONAL {{ {uri} f1:name        ?name        }}
          OPTIONAL {{ {uri} f1:nationality  ?nationality }}
          OPTIONAL {{ {uri} rdfs:seeAlso   ?url         }}
        }} LIMIT 1
    """)
    if not rows:
        messages.error(request, "Constructor not found.")
        return redirect("championship:admin_constructors")

    existing = rows[0]
    initial  = {"name": existing.get("name", ""), "nationality": existing.get("nationality", ""),
                "url": existing.get("url", "")}
    form = ConstructorForm(request.POST or initial)

    if request.method == "POST" and form.is_valid():
        d   = form.cleaned_data
        ref = _slug(d["name"])

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:constructorId {constructor_id}',
                   f'f1:constructorRef "{_sq(ref)}"',
                   f'f1:name "{_sq(d["name"])}"']
        if d.get("nationality"):
            triples.append(f'f1:nationality "{_sq(d["nationality"])}"')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }} ; INSERT DATA {{ {body} }}")
        messages.success(request, f'Constructor "{d["name"]}" updated.')
        return redirect("championship:admin_constructors")

    return render(request, "admin/constructor_form.html", {
        "form": form, "action": "Edit",
        "constructor_id": constructor_id, "label": existing.get("name", ""),
    })


@login_required(login_url="championship:admin_login")
def admin_constructor_delete(request, constructor_id: str):
    if request.method == "POST":
        db  = GraphDBClient()
        uri = _uri("constructor", constructor_id)
        rows = db.query(f"SELECT ?label WHERE {{ {uri} rdfs:label ?label }} LIMIT 1")
        label = rows[0]["label"] if rows else constructor_id
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }}")
        messages.success(request, f'Constructor "{label}" deleted.')
    return redirect("championship:admin_constructors")


# ── Circuits ──────────────────────────────────────────────────────────────────

@login_required(login_url="championship:admin_login")
def admin_circuits(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT ?circuitId ?label ?location ?country WHERE {
          ?c f1:circuitId ?circuitId ;
             rdfs:label    ?label .
          OPTIONAL { ?c f1:location ?location }
          OPTIONAL { ?c f1:country  ?country  }
        }
        ORDER BY ?label
    """)
    return render(request, "admin/circuits_list.html", {"circuits": rows})


@login_required(login_url="championship:admin_login")
def admin_circuit_add(request):
    form = CircuitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        db = GraphDBClient()
        d  = form.cleaned_data
        new_id = _next_id(db, "circuitId")
        ref    = _slug(d["name"])
        uri    = _uri("circuit", new_id)

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:circuitId {new_id}',
                   f'f1:circuitRef "{_sq(ref)}"',
                   f'f1:name "{_sq(d["name"])}"']
        if d.get("location"):
            triples.append(f'f1:location "{_sq(d["location"])}"')
        if d.get("country"):
            triples.append(f'f1:country "{_sq(d["country"])}"')
        if d.get("lat") is not None:
            triples.append(f'f1:lat {d["lat"]}')
        if d.get("lng") is not None:
            triples.append(f'f1:lng {d["lng"]}')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"INSERT DATA {{ {body} }}")
        messages.success(request, f'Circuit "{d["name"]}" added.')
        return redirect("championship:admin_circuits")

    return render(request, "admin/circuit_form.html", {"form": form, "action": "Add"})


@login_required(login_url="championship:admin_login")
def admin_circuit_edit(request, circuit_id: str):
    db  = GraphDBClient()
    uri = _uri("circuit", circuit_id)

    rows = db.query(f"""
        SELECT ?name ?location ?country ?lat ?lng ?url WHERE {{
          {uri} f1:circuitId ?anyId .
          OPTIONAL {{ {uri} f1:name     ?name     }}
          OPTIONAL {{ {uri} f1:location ?location }}
          OPTIONAL {{ {uri} f1:country  ?country  }}
          OPTIONAL {{ {uri} f1:lat      ?lat      }}
          OPTIONAL {{ {uri} f1:lng      ?lng      }}
          OPTIONAL {{ {uri} rdfs:seeAlso ?url     }}
        }} LIMIT 1
    """)
    if not rows:
        messages.error(request, "Circuit not found.")
        return redirect("championship:admin_circuits")

    existing = rows[0]
    initial  = {k: existing.get(k, "") for k in ("name", "location", "country", "lat", "lng", "url")}
    form = CircuitForm(request.POST or initial)

    if request.method == "POST" and form.is_valid():
        d   = form.cleaned_data
        ref = _slug(d["name"])

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:circuitId {circuit_id}',
                   f'f1:circuitRef "{_sq(ref)}"',
                   f'f1:name "{_sq(d["name"])}"']
        if d.get("location"):
            triples.append(f'f1:location "{_sq(d["location"])}"')
        if d.get("country"):
            triples.append(f'f1:country "{_sq(d["country"])}"')
        if d.get("lat") is not None:
            triples.append(f'f1:lat {d["lat"]}')
        if d.get("lng") is not None:
            triples.append(f'f1:lng {d["lng"]}')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }} ; INSERT DATA {{ {body} }}")
        messages.success(request, f'Circuit "{d["name"]}" updated.')
        return redirect("championship:admin_circuits")

    return render(request, "admin/circuit_form.html", {
        "form": form, "action": "Edit",
        "circuit_id": circuit_id, "label": existing.get("name", ""),
    })


@login_required(login_url="championship:admin_login")
def admin_circuit_delete(request, circuit_id: str):
    if request.method == "POST":
        db  = GraphDBClient()
        uri = _uri("circuit", circuit_id)
        rows = db.query(f"SELECT ?label WHERE {{ {uri} rdfs:label ?label }} LIMIT 1")
        label = rows[0]["label"] if rows else circuit_id
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }}")
        messages.success(request, f'Circuit "{label}" deleted.')
    return redirect("championship:admin_circuits")


# ── Races ─────────────────────────────────────────────────────────────────────

def _circuit_choices(db: GraphDBClient) -> list[tuple[str, str]]:
    rows = db.query("""
        SELECT ?circuitId ?label WHERE {
          ?c f1:circuitId ?circuitId ;
             rdfs:label    ?label .
        } ORDER BY ?label
    """)
    return [("", "— Select circuit —")] + [(r["circuitId"], r["label"]) for r in rows]


@login_required(login_url="championship:admin_login")
def admin_races(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT ?raceId ?label ?year ?round ?circuitLabel WHERE {
          ?r f1:raceId  ?raceId ;
             rdfs:label  ?label ;
             f1:year     ?year ;
             f1:round    ?round .
          OPTIONAL {
            ?r f1:circuit ?c .
            ?c rdfs:label ?circuitLabel .
          }
        }
        ORDER BY DESC(?year) ?round
    """)
    return render(request, "admin/races_list.html", {"races": rows})


@login_required(login_url="championship:admin_login")
def admin_race_add(request):
    db      = GraphDBClient()
    choices = _circuit_choices(db)
    form    = RaceForm(request.POST or None, circuit_choices=choices)

    if request.method == "POST" and form.is_valid():
        d      = form.cleaned_data
        new_id = _next_id(db, "raceId")
        uri    = _uri("race", new_id)
        c_uri  = _uri("circuit", d["circuit_id"])

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:raceId {new_id}',
                   f'f1:name "{_sq(d["name"])}"',
                   f'f1:year "{d["year"]}"^^xsd:gYear',
                   f'f1:round {d["round"]}',
                   f'f1:circuit {c_uri}']
        if d.get("date"):
            triples.append(f'f1:date "{d["date"]}"^^xsd:date')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"INSERT DATA {{ {body} }}")
        messages.success(request, f'Race "{d["name"]}" added.')
        return redirect("championship:admin_races")

    return render(request, "admin/race_form.html", {"form": form, "action": "Add"})


@login_required(login_url="championship:admin_login")
def admin_race_edit(request, race_id: str):
    db  = GraphDBClient()
    uri = _uri("race", race_id)

    rows = db.query(f"""
        SELECT ?name ?year ?round ?circuitId ?date ?url WHERE {{
          {uri} f1:raceId ?anyId .
          OPTIONAL {{ {uri} f1:name    ?name    }}
          OPTIONAL {{ {uri} f1:year    ?year    }}
          OPTIONAL {{ {uri} f1:round   ?round   }}
          OPTIONAL {{ {uri} f1:circuit ?circuit .
                      ?circuit f1:circuitId ?circuitId }}
          OPTIONAL {{ {uri} f1:date    ?date    }}
          OPTIONAL {{ {uri} rdfs:seeAlso ?url   }}
        }} LIMIT 1
    """)
    if not rows:
        messages.error(request, "Race not found.")
        return redirect("championship:admin_races")

    existing = rows[0]
    choices  = _circuit_choices(db)
    initial  = {
        "name":       existing.get("name", ""),
        "year":       existing.get("year", ""),
        "round":      existing.get("round", ""),
        "circuit_id": existing.get("circuitId", ""),
        "date":       existing.get("date", ""),
        "url":        existing.get("url", ""),
    }
    form = RaceForm(request.POST or initial, circuit_choices=choices)

    if request.method == "POST" and form.is_valid():
        d     = form.cleaned_data
        c_uri = _uri("circuit", d["circuit_id"])

        triples = [f'{uri} rdfs:label "{_sq(d["name"])}"',
                   f'f1:raceId {race_id}',
                   f'f1:name "{_sq(d["name"])}"',
                   f'f1:year "{d["year"]}"^^xsd:gYear',
                   f'f1:round {d["round"]}',
                   f'f1:circuit {c_uri}']
        if d.get("date"):
            triples.append(f'f1:date "{d["date"]}"^^xsd:date')
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }} ; INSERT DATA {{ {body} }}")
        messages.success(request, f'Race "{d["name"]}" updated.')
        return redirect("championship:admin_races")

    return render(request, "admin/race_form.html", {
        "form": form, "action": "Edit",
        "race_id": race_id, "label": existing.get("name", ""),
    })


@login_required(login_url="championship:admin_login")
def admin_race_delete(request, race_id: str):
    if request.method == "POST":
        db  = GraphDBClient()
        uri = _uri("race", race_id)
        rows = db.query(f"SELECT ?label WHERE {{ {uri} rdfs:label ?label }} LIMIT 1")
        label = rows[0]["label"] if rows else race_id
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }}")
        messages.success(request, f'Race "{label}" deleted.')
    return redirect("championship:admin_races")


# ── Seasons ───────────────────────────────────────────────────────────────────

@login_required(login_url="championship:admin_login")
def admin_seasons(request):
    db = GraphDBClient()
    rows = db.query("""
        SELECT ?year ?url WHERE {
          ?s f1:seasonYear ?year .
          OPTIONAL { ?s rdfs:seeAlso ?url }
        }
        ORDER BY DESC(?year)
    """)
    # Fallback: seasons are sometimes just year literals on race entities
    if not rows:
        rows = db.query("""
            SELECT DISTINCT ?year WHERE {
              ?r f1:year ?year .
            }
            ORDER BY DESC(?year)
        """)
    return render(request, "admin/seasons_list.html", {"seasons": rows})


@login_required(login_url="championship:admin_login")
def admin_season_add(request):
    form = SeasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        db  = GraphDBClient()
        d   = form.cleaned_data
        uri = f"<{RESOURCE_BASE}season/{d['year']}>"

        triples = [f'{uri} f1:seasonYear "{d["year"]}"^^xsd:gYear',
                   f'rdfs:label "Season {d["year"]}"']
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"INSERT DATA {{ {body} }}")
        messages.success(request, f'Season {d["year"]} added.')
        return redirect("championship:admin_seasons")

    return render(request, "admin/season_form.html", {"form": form, "action": "Add"})


@login_required(login_url="championship:admin_login")
def admin_season_edit(request, year: str):
    db  = GraphDBClient()
    uri = f"<{RESOURCE_BASE}season/{year}>"

    rows = db.query(f"""
        SELECT ?url WHERE {{
          {uri} f1:seasonYear ?y .
          OPTIONAL {{ {uri} rdfs:seeAlso ?url }}
        }} LIMIT 1
    """)

    initial  = {"year": year, "url": rows[0].get("url", "") if rows else ""}
    form     = SeasonForm(request.POST or initial)

    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        triples = [f'{uri} f1:seasonYear "{d["year"]}"^^xsd:gYear',
                   f'rdfs:label "Season {d["year"]}"']
        if d.get("url"):
            triples.append(f'rdfs:seeAlso <{d["url"]}>')

        body = " ;\n  ".join(triples) + " ."
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }} ; INSERT DATA {{ {body} }}")
        messages.success(request, f'Season {d["year"]} updated.')
        return redirect("championship:admin_seasons")

    return render(request, "admin/season_form.html", {
        "form": form, "action": "Edit", "year": year,
    })


@login_required(login_url="championship:admin_login")
def admin_season_delete(request, year: str):
    if request.method == "POST":
        db  = GraphDBClient()
        uri = f"<{RESOURCE_BASE}season/{year}>"
        db.run_update(f"DELETE WHERE {{ {uri} ?p ?o }}")
        messages.success(request, f'Season {year} deleted.')
    return redirect("championship:admin_seasons")
