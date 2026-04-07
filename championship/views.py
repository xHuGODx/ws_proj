from __future__ import annotations

from datetime import date

from django.shortcuts import render

from .services.graphdb import GraphDBClient

_COMING_SOON = "championship/coming_soon.html"
RESOURCE_BASE = "http://example.org/resource/"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _calc_age(dob: str) -> int | str:
    try:
        birth = date.fromisoformat(dob)
        today = date.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except Exception:
        return ""


def _driver_id_from_uri(uri: str) -> str:
    return uri.rstrip("/").split("/")[-1]


# ── Home ──────────────────────────────────────────────────────────────────────

def home(request):
    graphdb = GraphDBClient()
    stats = [
        {"value": "75",   "label": "Seasons"},
        {"value": "77",   "label": "Circuits"},
        {"value": "861",  "label": "Drivers"},
        {"value": "212",  "label": "Constructors"},
        {"value": "1125", "label": "Races"},
    ]
    return render(request, "championship/home.html", {
        "graphdb": graphdb.healthcheck(),
        "stats": stats,
    })


# ── Drivers list ──────────────────────────────────────────────────────────────

def drivers(request):
    db = GraphDBClient()

    # Anchor on f1:driverId (property lookup) — avoids rdf:type inference which is very slow.
    rows = db.query("""
        SELECT ?uri ?label ?nationality ?code ?dob ?driverId WHERE {
          ?uri f1:driverId ?driverId ;
               rdfs:label  ?label .
          OPTIONAL { ?uri f1:nationality ?nationality }
          OPTIONAL { ?uri f1:code ?code }
          OPTIONAL { ?uri f1:dob  ?dob  }
        }
    """)

    race_counts = {
        r["driver"]: int(r["races"])
        for r in db.query("""
            SELECT ?driver (COUNT(*) AS ?races) WHERE {
              ?r f1:resultId ?anyId ; f1:driver ?driver .
            } GROUP BY ?driver
        """)
    }

    # Single query for positions 1/2/3 — builds wins, seconds, thirds, podiums
    podium_breakdown: dict[str, dict[int, int]] = {}
    for r in db.query("""
        SELECT ?driver ?pos (COUNT(*) AS ?cnt) WHERE {
          ?r f1:resultId ?anyId ;
             f1:driver ?driver ;
             f1:positionOrder ?pos .
          FILTER(?pos IN (1, 2, 3))
        } GROUP BY ?driver ?pos
    """):
        uri_key = r["driver"]
        pos     = int(r["pos"])
        cnt     = int(r["cnt"])
        podium_breakdown.setdefault(uri_key, {1: 0, 2: 0, 3: 0})[pos] = cnt

    all_drivers = []
    for r in rows:
        dob  = r.get("dob", "")
        uri  = r.get("uri", "")
        pdat = podium_breakdown.get(uri, {1: 0, 2: 0, 3: 0})
        wins    = pdat.get(1, 0)
        seconds = pdat.get(2, 0)
        thirds  = pdat.get(3, 0)
        all_drivers.append({
            "id":          r.get("driverId", ""),
            "uri":         uri,
            "label":       r.get("label", ""),
            "nationality": r.get("nationality", ""),
            "code":        r.get("code", ""),
            "born":        dob[:4] if dob else "",
            "races":       race_counts.get(uri, 0),
            "wins":        wins,
            "seconds":     seconds,
            "thirds":      thirds,
            "podiums":     wins + seconds + thirds,
        })

    # Podium sidebar — always from full unfiltered set
    podium = sorted(all_drivers, key=lambda d: d["wins"], reverse=True)[:3]

    # Nationalities for filter dropdown
    nationalities = sorted({d["nationality"] for d in all_drivers if d["nationality"]})

    # Filtering
    q           = request.GET.get("q", "").strip()
    nationality = request.GET.get("nationality", "")
    medal    = request.GET.get("medal", "")   # "", "gold", "silver", "bronze"
    filtered = all_drivers

    if q:
        ql = q.lower()
        filtered = [d for d in filtered if ql in d["label"].lower() or ql in d["code"].lower()]
    if nationality:
        filtered = [d for d in filtered if d["nationality"] == nationality]
    if medal == "gold":
        filtered = [d for d in filtered if d["wins"]    > 0]
    elif medal == "silver":
        filtered = [d for d in filtered if d["seconds"] > 0]
    elif medal == "bronze":
        filtered = [d for d in filtered if d["thirds"]  > 0]

    # Sorting
    sort  = request.GET.get("sort", "label")
    order = request.GET.get("order", "asc")
    key_map = {
        "label":   lambda d: d["label"].lower(),
        "wins":    lambda d: d["wins"],
        "podiums": lambda d: d["podiums"],
        "races":   lambda d: d["races"],
        "born":    lambda d: d["born"] or "0",
    }
    if sort in key_map:
        filtered.sort(key=key_map[sort], reverse=(order == "desc"))

    # Pagination
    per_page    = 20
    total       = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(1, min(int(request.GET.get("page", 1)), total_pages))
    page_drivers = filtered[(page - 1) * per_page: page * per_page]

    # Page range for pagination widget
    page_range = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    return render(request, "championship/drivers.html", {
        "drivers":       page_drivers,
        "podium":        podium,
        "nationalities": nationalities,
        "q":             q,
        "nationality":   nationality,
        "medal":         medal,
        "sort":          sort,
        "order":         order,
        "page":          page,
        "total_pages":   total_pages,
        "total":         total,
        "page_range":    page_range,
    })


# ── Driver detail ─────────────────────────────────────────────────────────────

def driver_detail(request, driver_id: str):
    db  = GraphDBClient()
    uri = f"<{RESOURCE_BASE}driver/{driver_id}>"

    # Basic info
    info_rows = db.query(f"""
        SELECT ?label ?nationality ?code ?dob ?number ?driverRef WHERE {{
          {uri} rdfs:label ?label .
          OPTIONAL {{ {uri} f1:nationality ?nationality }}
          OPTIONAL {{ {uri} f1:code       ?code       }}
          OPTIONAL {{ {uri} f1:dob        ?dob        }}
          OPTIONAL {{ {uri} f1:number     ?number     }}
          OPTIONAL {{ {uri} f1:driverRef  ?driverRef  }}
        }}
    """)
    if not info_rows:
        return render(request, "championship/coming_soon.html", {"page": "Driver not found"})
    info = info_rows[0]
    dob  = info.get("dob", "")
    info["age"] = _calc_age(dob)

    # Anchor on f1:resultId to avoid rdf:type inference cost.
    result_rows = db.query(f"""
        SELECT ?positionOrder ?points WHERE {{
          ?r f1:resultId ?anyId ;
             f1:driver {uri} ;
             f1:positionOrder ?positionOrder .
          OPTIONAL {{ ?r f1:points ?points }}
        }}
    """)
    wins = seconds = thirds = total_races = 0
    total_points = 0.0
    for r in result_rows:
        pos = int(r.get("positionOrder", 0))
        total_races += 1
        if pos == 1: wins    += 1
        if pos == 2: seconds += 1
        if pos == 3: thirds  += 1
        try:
            total_points += float(r.get("points", 0))
        except (ValueError, TypeError):
            pass

    # Constructor career
    constructor_rows = db.query(f"""
        SELECT DISTINCT ?constructorLabel
               (MIN(?year) AS ?firstYear)
               (MAX(?year) AS ?lastYear)
        WHERE {{
          ?r f1:resultId ?anyId ;
             f1:driver {uri} ;
             f1:constructor ?constructor ;
             f1:race ?race .
          ?race f1:year ?year .
          ?constructor rdfs:label ?constructorLabel .
        }}
        GROUP BY ?constructorLabel
        ORDER BY ?firstYear
    """)

    # Top circuits
    circuit_rows = db.query(f"""
        SELECT ?circuitLabel (COUNT(*) AS ?count) WHERE {{
          ?r f1:resultId ?anyId ;
             f1:driver {uri} ;
             f1:race ?race .
          ?race f1:circuit ?circuit .
          ?circuit rdfs:label ?circuitLabel .
        }}
        GROUP BY ?circuitLabel
        ORDER BY DESC(?count)
        LIMIT 6
    """)

    # Wikipedia URL
    wiki_rows = db.query(f"""
        SELECT ?url WHERE {{
          {uri} rdfs:seeAlso ?url .
        }}
        LIMIT 1
    """)
    wiki_url = wiki_rows[0]["url"] if wiki_rows else ""

    return render(request, "championship/driver_detail.html", {
        "info":         info,
        "driver_id":    driver_id,
        "wins":         wins,
        "seconds":      seconds,
        "thirds":       thirds,
        "total_races":  total_races,
        "total_points": int(total_points),
        "constructors": constructor_rows,
        "circuits":     circuit_rows,
        "wiki_url":     wiki_url,
    })


# ── Stubs ─────────────────────────────────────────────────────────────────────

def constructors(request):
    db = GraphDBClient()

    # Basic info — anchor on f1:constructorId
    rows = db.query("""
        SELECT ?uri ?label ?nationality ?constructorId WHERE {
          ?uri f1:constructorId ?constructorId ;
               rdfs:label ?label .
          OPTIONAL { ?uri f1:nationality ?nationality }
        }
    """)

    # Race counts, first year, distinct pilots — anchored on f1:resultId
    stats: dict[str, dict] = {}
    for r in db.query("""
        SELECT ?constructor
               (COUNT(DISTINCT ?race)   AS ?races)
               (MIN(?year)              AS ?firstYear)
               (COUNT(DISTINCT ?driver) AS ?pilots)
        WHERE {
          ?res f1:resultId ?anyId ;
               f1:constructor ?constructor ;
               f1:race ?race ;
               f1:driver ?driver .
          ?race f1:year ?year .
        } GROUP BY ?constructor
    """):
        stats[r["constructor"]] = {
            "races":      int(r["races"]),
            "first_year": r.get("firstYear", ""),
            "pilots":     int(r["pilots"]),
        }

    # Podium breakdown — positions 1/2/3
    podium_breakdown: dict[str, dict[int, int]] = {}
    for r in db.query("""
        SELECT ?constructor ?pos (COUNT(*) AS ?cnt) WHERE {
          ?res f1:resultId ?anyId ;
               f1:constructor ?constructor ;
               f1:positionOrder ?pos .
          FILTER(?pos IN (1, 2, 3))
        } GROUP BY ?constructor ?pos
    """):
        key = r["constructor"]
        pos = int(r["pos"])
        cnt = int(r["cnt"])
        podium_breakdown.setdefault(key, {1: 0, 2: 0, 3: 0})[pos] = cnt

    all_constructors = []
    for r in rows:
        uri  = r.get("uri", "")
        s    = stats.get(uri, {})
        pdat = podium_breakdown.get(uri, {1: 0, 2: 0, 3: 0})
        wins    = pdat.get(1, 0)
        seconds = pdat.get(2, 0)
        thirds  = pdat.get(3, 0)
        all_constructors.append({
            "id":          r.get("constructorId", ""),
            "uri":         uri,
            "label":       r.get("label", ""),
            "nationality": r.get("nationality", ""),
            "races":       s.get("races", 0),
            "first_year":  s.get("first_year", ""),
            "pilots":      s.get("pilots", 0),
            "wins":        wins,
            "seconds":     seconds,
            "thirds":      thirds,
            "podiums":     wins + seconds + thirds,
        })

    # Sidebar podium — top 3 by wins
    podium = sorted(all_constructors, key=lambda c: c["wins"], reverse=True)[:3]

    # Nationalities for filter dropdown
    nationalities = sorted({c["nationality"] for c in all_constructors if c["nationality"]})

    # Filtering
    q           = request.GET.get("q", "").strip()
    nationality = request.GET.get("nationality", "")
    filtered    = all_constructors

    if q:
        filtered = [c for c in filtered if q.lower() in c["label"].lower()]
    if nationality:
        filtered = [c for c in filtered if c["nationality"] == nationality]

    # Sorting
    sort  = request.GET.get("sort", "label")
    order = request.GET.get("order", "asc")
    key_map = {
        "label":      lambda c: c["label"].lower(),
        "wins":       lambda c: c["wins"],
        "podiums":    lambda c: c["podiums"],
        "races":      lambda c: c["races"],
        "first_year": lambda c: c["first_year"] or "0",
        "pilots":     lambda c: c["pilots"],
    }
    if sort in key_map:
        filtered.sort(key=key_map[sort], reverse=(order == "desc"))

    # Pagination
    per_page    = 20
    total       = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(1, min(int(request.GET.get("page", 1)), total_pages))
    page_items  = filtered[(page - 1) * per_page: page * per_page]
    page_range  = list(range(max(1, page - 2), min(total_pages, page + 2) + 1))

    return render(request, "championship/constructors.html", {
        "constructors":  page_items,
        "podium":        podium,
        "nationalities": nationalities,
        "q":             q,
        "nationality":   nationality,
        "sort":          sort,
        "order":         order,
        "page":          page,
        "total_pages":   total_pages,
        "total":         total,
        "page_range":    page_range,
    })


def seasons(request):
    return render(request, _COMING_SOON, {"page": "Seasons"})


def races(request):
    return render(request, _COMING_SOON, {"page": "Races"})


def circuits(request):
    return render(request, _COMING_SOON, {"page": "Circuits"})


def sparql(request):
    return render(request, _COMING_SOON, {"page": "SPARQL"})
