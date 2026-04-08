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
        "offset":        (page - 1) * per_page,
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
    medal       = request.GET.get("medal", "")
    filtered    = all_constructors

    if q:
        filtered = [c for c in filtered if q.lower() in c["label"].lower()]
    if nationality:
        filtered = [c for c in filtered if c["nationality"] == nationality]
    if medal == "gold":
        filtered = [c for c in filtered if c["wins"]    > 0]
    elif medal == "silver":
        filtered = [c for c in filtered if c["seconds"] > 0]
    elif medal == "bronze":
        filtered = [c for c in filtered if c["thirds"]  > 0]

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
        "medal":         medal,
        "sort":          sort,
        "order":         order,
        "page":          page,
        "total_pages":   total_pages,
        "total":         total,
        "page_range":    page_range,
        "offset":        (page - 1) * per_page,
    })


# ── Constructor detail ────────────────────────────────────────────────────────

def constructor_detail(request, constructor_id: str):
    db  = GraphDBClient()
    uri = f"<{RESOURCE_BASE}constructor/{constructor_id}>"

    # Basic info
    info_rows = db.query(f"""
        SELECT ?label ?nationality ?constructorRef WHERE {{
          {uri} rdfs:label ?label .
          OPTIONAL {{ {uri} f1:nationality     ?nationality     }}
          OPTIONAL {{ {uri} f1:constructorRef  ?constructorRef  }}
        }}
    """)
    if not info_rows:
        return render(request, _COMING_SOON, {"page": "Constructor not found"})
    info = info_rows[0]

    # Wikipedia URL
    wiki_rows = db.query(f"""
        SELECT ?url WHERE {{ {uri} rdfs:seeAlso ?url . }} LIMIT 1
    """)
    wiki_url = wiki_rows[0]["url"] if wiki_rows else ""

    # Overall race stats — anchor on f1:resultId
    result_rows = db.query(f"""
        SELECT ?positionOrder ?year WHERE {{
          ?r f1:resultId ?anyId ;
             f1:constructor {uri} ;
             f1:positionOrder ?positionOrder ;
             f1:race ?race .
          ?race f1:year ?year .
        }}
    """)
    wins = seconds = thirds = total_races = 0
    years_set: set[str] = set()
    for r in result_rows:
        pos = int(r.get("positionOrder", 0))
        total_races += 1
        if pos == 1: wins    += 1
        if pos == 2: seconds += 1
        if pos == 3: thirds  += 1
        y = r.get("year", "")
        if y:
            years_set.add(y)
    first_year = min(years_set) if years_set else ""
    last_year  = max(years_set) if years_set else ""

    # Top circuits by appearances
    circuit_rows = db.query(f"""
        SELECT ?circuitLabel (COUNT(*) AS ?count) WHERE {{
          ?r f1:resultId ?anyId ;
             f1:constructor {uri} ;
             f1:race ?race .
          ?race f1:circuit ?circuit .
          ?circuit rdfs:label ?circuitLabel .
        }}
        GROUP BY ?circuitLabel
        ORDER BY DESC(?count)
        LIMIT 6
    """)

    # Pilots — stats per driver for this constructor
    pilot_rows = db.query(f"""
        SELECT ?driver ?driverLabel
               (COUNT(*) AS ?races)
               (SUM(IF(?pos = 1, 1, 0)) AS ?wins)
               (SUM(IF(?pos IN (1,2,3), 1, 0)) AS ?podiums)
               (MIN(?year) AS ?firstYear)
               (MAX(?year) AS ?lastYear)
        WHERE {{
          ?r f1:resultId ?anyId ;
             f1:constructor {uri} ;
             f1:driver ?driver ;
             f1:positionOrder ?pos ;
             f1:race ?race .
          ?race f1:year ?year .
          ?driver rdfs:label ?driverLabel .
        }}
        GROUP BY ?driver ?driverLabel
        ORDER BY DESC(?wins) DESC(?races)
    """)

    pilots = []
    for r in pilot_rows:
        driver_uri = r.get("driver", "")
        driver_id_val = driver_uri.rstrip("/").split("/")[-1]
        pilots.append({
            "id":         driver_id_val,
            "label":      r.get("driverLabel", ""),
            "races":      int(r.get("races", 0)),
            "wins":       int(r.get("wins", 0)),
            "podiums":    int(r.get("podiums", 0)),
            "first_year": r.get("firstYear", ""),
            "last_year":  r.get("lastYear", ""),
        })

    return render(request, "championship/constructor_detail.html", {
        "info":            info,
        "constructor_id":  constructor_id,
        "wiki_url":        wiki_url,
        "wins":            wins,
        "seconds":         seconds,
        "thirds":          thirds,
        "total_races":     total_races,
        "first_year":      first_year,
        "last_year":       last_year,
        "circuits":        circuit_rows,
        "pilots":          pilots,
    })


# ── Circuit detail ────────────────────────────────────────────────────────────

def circuit_detail(request, circuit_id: str):
    db  = GraphDBClient()
    uri = f"<{RESOURCE_BASE}circuit/{circuit_id}>"

    # Basic info
    info_rows = db.query(f"""
        SELECT ?label ?location ?country ?circuitRef ?lat ?lng ?alt WHERE {{
          {uri} rdfs:label ?label .
          OPTIONAL {{ {uri} f1:location   ?location   }}
          OPTIONAL {{ {uri} f1:country    ?country    }}
          OPTIONAL {{ {uri} f1:circuitRef ?circuitRef }}
          OPTIONAL {{ {uri} f1:lat        ?lat        }}
          OPTIONAL {{ {uri} f1:lng        ?lng        }}
          OPTIONAL {{ {uri} f1:alt        ?alt        }}
        }}
    """)
    if not info_rows:
        return render(request, _COMING_SOON, {"page": "Circuit not found"})
    info = info_rows[0]

    wiki_rows = db.query(f"SELECT ?url WHERE {{ {uri} rdfs:seeAlso ?url . }} LIMIT 1")
    wiki_url = wiki_rows[0]["url"] if wiki_rows else ""

    # Race history with winner — anchor on f1:circuit (unique to races)
    race_rows = db.query(f"""
        SELECT ?year ?raceName ?winnerLabel ?winnerDriverId ?constructorLabel WHERE {{
          ?race f1:circuit {uri} ;
                f1:year    ?year ;
                rdfs:label ?raceName .
          OPTIONAL {{
            ?res f1:resultId ?anyId ;
                 f1:race ?race ;
                 f1:positionOrder 1 ;
                 f1:driver ?winner ;
                 f1:constructor ?ctor .
            ?winner rdfs:label ?winnerLabel .
            ?winner f1:driverId ?winnerDriverId .
            ?ctor   rdfs:label  ?constructorLabel .
          }}
        }}
        ORDER BY DESC(?year)
    """)

    # Build year → race_count map for timeline
    year_counts: dict[str, int] = {}
    for r in race_rows:
        y = r.get("year", "")
        if y:
            year_counts[y] = year_counts.get(y, 0) + 1

    total_races = sum(year_counts.values())
    first_year  = min(year_counts.keys(), default="")
    last_year   = max(year_counts.keys(), default="")

    # Global latest year to determine active status
    max_yr_rows = db.query("""
        SELECT (MAX(?year) AS ?maxYear) WHERE { ?r f1:circuit ?c ; f1:year ?year . }
    """)
    global_max_year = max_yr_rows[0].get("maxYear", "0") if max_yr_rows else "0"
    active = last_year == global_max_year

    # Year-range timeline (fill gaps between first and last year)
    timeline: list[dict] = []
    if year_counts:
        for y in range(int(first_year), int(last_year) + 1):
            timeline.append({"year": y, "races": year_counts.get(str(y), 0)})

    # Top winners at this circuit
    driver_wins: dict[tuple, int] = {}
    for r in race_rows:
        w = r.get("winnerLabel", "")
        wid = r.get("winnerDriverId", "")
        if w:
            driver_wins[(w, wid)] = driver_wins.get((w, wid), 0) + 1
    unique_winners_count = len(driver_wins)
    top_winners = [
        {"label": k[0], "id": k[1], "wins": v}
        for k, v in sorted(driver_wins.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # Fastest laps — anchor with f1:position which exists on lap_times but NOT
    # on pit_stops (which has f1:stop). Both have f1:lap and f1:milliseconds,
    # so this triple distinguishes the two entity types.
    fastest_rows = db.query(f"""
        SELECT ?driverLabel ?driverId ?time ?ms ?year WHERE {{
          ?race f1:circuit {uri} ;
                f1:year    ?year .
          ?lt f1:race         ?race ;
              f1:driver       ?driver ;
              f1:milliseconds ?ms ;
              f1:time         ?time ;
              f1:lap          ?lap ;
              f1:position     ?pos .
          ?driver rdfs:label  ?driverLabel .
          ?driver f1:driverId ?driverId .
          FILTER(?ms > 60000)
        }}
        ORDER BY ASC(?ms)
        LIMIT 5
    """)

    return render(request, "championship/circuit_detail.html", {
        "info":                  info,
        "circuit_id":            circuit_id,
        "wiki_url":              wiki_url,
        "race_rows":             race_rows,
        "total_races":           total_races,
        "first_year":            first_year,
        "last_year":             last_year,
        "active":                active,
        "timeline":              timeline,
        "top_winners":           top_winners,
        "unique_winners_count":  unique_winners_count,
        "fastest":               fastest_rows,
    })


def seasons(request):
    db = GraphDBClient()

    # ── Q1: Aggregate stats per season ────────────────────────────────────────
    # Anchor on f1:resultId; join to race for year.
    stat_rows = db.query("""
        SELECT ?year
               (COUNT(DISTINCT ?race)        AS ?races)
               (COUNT(DISTINCT ?driver)      AS ?drivers)
               (COUNT(DISTINCT ?constructor) AS ?constructors)
        WHERE {
          ?res f1:resultId ?anyId ;
               f1:race ?race ;
               f1:driver ?driver ;
               f1:constructor ?constructor .
          ?race f1:year ?year .
        } GROUP BY ?year
        ORDER BY DESC(?year)
    """)

    # ── Q2: Top race-winner per season ────────────────────────────────────────
    winner_rows = db.query("""
        SELECT ?year ?driverLabel ?driverId (COUNT(*) AS ?wins) WHERE {
          ?res f1:resultId ?anyId ;
               f1:race ?race ;
               f1:positionOrder 1 ;
               f1:driver ?driver .
          ?race f1:year ?year .
          ?driver rdfs:label ?driverLabel ;
                  f1:driverId ?driverId .
        } GROUP BY ?year ?driverLabel ?driverId
        ORDER BY DESC(?year) DESC(?wins)
    """)

    top_winner: dict[str, dict] = {}
    for r in winner_rows:
        y = r.get("year", "")
        if y not in top_winner:
            top_winner[y] = r

    all_seasons = []
    for r in stat_rows:
        y = r.get("year", "")
        w = top_winner.get(y, {})
        all_seasons.append({
            "year":              y,
            "races":             int(r.get("races", 0)),
            "drivers":           int(r.get("drivers", 0)),
            "constructors":      int(r.get("constructors", 0)),
            "top_winner_label":  w.get("driverLabel", ""),
            "top_winner_id":     w.get("driverId", ""),
            "top_winner_wins":   int(w.get("wins", 0)) if w.get("wins") else 0,
        })

    return render(request, "championship/seasons.html", {
        "seasons": all_seasons,
    })


def season_detail(request, year: str):
    db = GraphDBClient()
    # Validate year is a 4-digit number
    if not year.isdigit() or len(year) != 4:
        return render(request, _COMING_SOON, {"page": "Season not found"})

    # ── Q1: Race calendar ─────────────────────────────────────────────────────
    # GROUP BY deduplicates races that have >1 positionOrder=1 result (e.g.
    # sprint-weekend races which may have both a sprint and race winner row).
    race_rows = db.query(f"""
        SELECT ?raceId ?raceName ?round ?date
               ?circuitLabel ?circuitCountry
               (SAMPLE(?winnerLabel) AS ?winnerLabel)
               (SAMPLE(?winnerDriverId) AS ?winnerDriverId)
               (SAMPLE(?winnerConstructor) AS ?winnerConstructor) WHERE {{
          ?race f1:round ?round ;
                f1:year ?yr ;
                f1:raceId ?raceId ;
                rdfs:label ?raceName .
          FILTER(STR(?yr) = "{year}")
          OPTIONAL {{ ?race f1:date ?date }}
          OPTIONAL {{
            ?race f1:circuit ?circuit .
            ?circuit rdfs:label ?circuitLabel .
            OPTIONAL {{ ?circuit f1:country ?circuitCountry }}
          }}
          OPTIONAL {{
            ?res f1:resultId ?anyId ;
                 f1:race ?race ;
                 f1:positionOrder 1 ;
                 f1:driver ?winner ;
                 f1:constructor ?ctor .
            ?winner rdfs:label ?winnerLabel ;
                    f1:driverId ?winnerDriverId .
            ?ctor   rdfs:label ?winnerConstructor .
          }}
        }}
        GROUP BY ?raceId ?raceName ?round ?date ?circuitLabel ?circuitCountry
        ORDER BY ?round
    """)

    if not race_rows:
        return render(request, _COMING_SOON, {"page": f"Season {year} not found"})

    total_races = len(race_rows)

    # ── Q2: Driver standings (all rounds; keep last per driver in Python) ──────
    ds_rows = db.query(f"""
        SELECT ?driverLabel ?driverId ?points ?position ?wins ?round WHERE {{
          ?ds f1:driverStandingsId ?anyId ;
              f1:race ?race ;
              f1:driver ?driver ;
              f1:points ?points ;
              f1:position ?position ;
              f1:wins ?wins .
          ?race f1:year ?yr ; f1:round ?round .
          FILTER(STR(?yr) = "{year}")
          ?driver rdfs:label ?driverLabel ;
                  f1:driverId ?driverId .
        }}
        ORDER BY DESC(?round) ?position
    """)

    seen_drivers: set[str] = set()
    driver_standings = []
    for r in ds_rows:
        did = r.get("driverId", "")
        if did not in seen_drivers:
            seen_drivers.add(did)
            driver_standings.append(r)
    driver_standings.sort(key=lambda x: int(x.get("position", 999)))

    # ── Q3: Constructor standings (same pattern) ──────────────────────────────
    cs_rows = db.query(f"""
        SELECT ?constructorLabel ?constructorId ?points ?position ?wins ?round WHERE {{
          ?cs f1:constructorStandingsId ?anyId ;
              f1:race ?race ;
              f1:constructor ?constructor ;
              f1:points ?points ;
              f1:position ?position ;
              f1:wins ?wins .
          ?race f1:year ?yr ; f1:round ?round .
          FILTER(STR(?yr) = "{year}")
          ?constructor rdfs:label ?constructorLabel ;
                       f1:constructorId ?constructorId .
        }}
        ORDER BY DESC(?round) ?position
    """)

    seen_constructors: set[str] = set()
    constructor_standings = []
    for r in cs_rows:
        cid = r.get("constructorId", "")
        if cid not in seen_constructors:
            seen_constructors.add(cid)
            constructor_standings.append(r)
    constructor_standings.sort(key=lambda x: int(x.get("position", 999)))

    # Wikipedia URL for season entity
    season_uri = f"<{RESOURCE_BASE}season/{year}>"
    wiki_rows  = db.query(f"SELECT ?url WHERE {{ {season_uri} rdfs:seeAlso ?url . }} LIMIT 1")
    wiki_url   = wiki_rows[0]["url"] if wiki_rows else ""

    return render(request, "championship/season_detail.html", {
        "year":                   year,
        "wiki_url":               wiki_url,
        "race_calendar":          race_rows,
        "total_races":            total_races,
        "driver_standings":       driver_standings,
        "constructor_standings":  constructor_standings,
        "unique_drivers":         len(driver_standings),
        "unique_constructors":    len(constructor_standings),
    })


def races(request):
    db = GraphDBClient()

    # ── Query 1: All races with circuit info ──────────────────────────────────
    # Anchor on f1:round which exists ONLY in races.csv
    race_rows = db.query("""
        SELECT ?uri ?raceId ?label ?year ?round ?date ?circuitLabel ?circuitCountry WHERE {
          ?uri f1:round ?round ;
               f1:raceId ?raceId ;
               rdfs:label ?label ;
               f1:year ?year .
          OPTIONAL { ?uri f1:date ?date }
          OPTIONAL {
            ?uri f1:circuit ?circuit .
            ?circuit rdfs:label ?circuitLabel .
            OPTIONAL { ?circuit f1:country ?circuitCountry }
          }
        }
        ORDER BY DESC(?year) DESC(?round)
    """)

    # ── Query 2: Winners for all races ────────────────────────────────────────
    winner_rows = db.query("""
        SELECT ?race ?driverLabel ?driverId ?constructorLabel WHERE {
          ?res f1:resultId ?anyId ;
               f1:race ?race ;
               f1:positionOrder 1 ;
               f1:driver ?driver ;
               f1:constructor ?constructor .
          ?driver rdfs:label ?driverLabel ;
                  f1:driverId ?driverId .
          ?constructor rdfs:label ?constructorLabel .
        }
    """)
    winners = {r["race"]: r for r in winner_rows}

    # Build race list
    all_races = []
    for r in race_rows:
        uri = r.get("uri", "")
        w   = winners.get(uri, {})
        all_races.append({
            "id":                r.get("raceId", ""),
            "uri":               uri,
            "label":             r.get("label", ""),
            "year":              r.get("year", ""),
            "round":             int(r.get("round", 0)),
            "date":              r.get("date", ""),
            "circuit_label":     r.get("circuitLabel", ""),
            "circuit_country":   r.get("circuitCountry", ""),
            "winner_label":      w.get("driverLabel", ""),
            "winner_id":         w.get("driverId", ""),
            "constructor_label": w.get("constructorLabel", ""),
        })

    # ── Featured card: most recent race ──────────────────────────────────────
    featured = None
    if all_races:
        latest    = all_races[0]
        uri_term  = f"<{latest['uri']}>"

        # Top 3 finishers
        podium_rows = db.query(f"""
            SELECT ?positionOrder ?driverLabel ?driverId ?constructorLabel ?time ?points WHERE {{
              ?res f1:resultId ?anyId ;
                   f1:race {uri_term} ;
                   f1:positionOrder ?positionOrder ;
                   f1:driver ?driver ;
                   f1:constructor ?constructor .
              OPTIONAL {{ ?res f1:time   ?time   }}
              OPTIONAL {{ ?res f1:points ?points }}
              ?driver rdfs:label ?driverLabel ;
                      f1:driverId ?driverId .
              ?constructor rdfs:label ?constructorLabel .
              FILTER(?positionOrder IN (1, 2, 3))
            }}
            ORDER BY ?positionOrder
        """)

        stats_rows = db.query(f"""
            SELECT (COUNT(*) AS ?entries) (MAX(?laps) AS ?maxLaps) WHERE {{
              ?res f1:resultId ?anyId ;
                   f1:race {uri_term} ;
                   f1:laps ?laps .
            }}
        """)

        fl_rows = db.query(f"""
            SELECT ?driverLabel ?fastestLapTime WHERE {{
              ?res f1:resultId ?anyId ;
                   f1:race {uri_term} ;
                   f1:fastestLapSpeed ?speed ;
                   f1:fastestLapTime  ?fastestLapTime ;
                   f1:driver ?driver .
              ?driver rdfs:label ?driverLabel .
            }}
            ORDER BY DESC(?speed)
            LIMIT 1
        """)

        stats = stats_rows[0] if stats_rows else {}
        fl    = fl_rows[0] if fl_rows else {}

        fp = []
        for p in podium_rows:
            fp.append({
                "pos":               int(p.get("positionOrder", 99)),
                "driver_label":      p.get("driverLabel", ""),
                "driver_id":         p.get("driverId", ""),
                "constructor_label": p.get("constructorLabel", ""),
                "time":              p.get("time", ""),
                "points":            p.get("points", ""),
            })

        featured = {
            "race":               latest,
            "podium":             fp,
            "entries":            int(stats.get("entries", 0)),
            "total_laps":         stats.get("maxLaps", ""),
            "fastest_lap_time":   fl.get("fastestLapTime", ""),
            "fastest_lap_driver": fl.get("driverLabel", ""),
        }

    # Seasons dropdown
    seasons_list = sorted({r["year"] for r in all_races if r["year"]}, reverse=True)

    # Filtering
    q      = request.GET.get("q", "").strip()
    season = request.GET.get("season", "")
    filtered = list(all_races)

    if q:
        ql = q.lower()
        filtered = [r for r in filtered
                    if ql in r["label"].lower()
                    or ql in r["circuit_label"].lower()
                    or ql in r["circuit_country"].lower()]
    if season:
        filtered = [r for r in filtered if r["year"] == season]

    # Sorting
    sort  = request.GET.get("sort", "year")
    order = request.GET.get("order", "desc")
    key_map = {
        "label": lambda r: r["label"].lower(),
        "year":  lambda r: (r["year"], r["round"]),
        "round": lambda r: r["round"],
        "date":  lambda r: r["date"] or "",
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

    return render(request, "championship/races.html", {
        "races":       page_items,
        "featured":    featured,
        "seasons":     seasons_list,
        "q":           q,
        "season":      season,
        "sort":        sort,
        "order":       order,
        "page":        page,
        "total_pages": total_pages,
        "total":       total,
        "page_range":  page_range,
        "offset":      (page - 1) * per_page,
    })


def race_detail(request, race_id: str):
    db  = GraphDBClient()
    uri = f"<{RESOURCE_BASE}race/{race_id}>"

    # Basic info + circuit
    info_rows = db.query(f"""
        SELECT ?label ?year ?round ?date ?circuitLabel ?circuitCountry ?circuitId WHERE {{
          {uri} f1:round ?round ;
                rdfs:label ?label ;
                f1:year ?year .
          OPTIONAL {{ {uri} f1:date ?date }}
          OPTIONAL {{
            {uri} f1:circuit ?circuit .
            ?circuit rdfs:label ?circuitLabel .
            OPTIONAL {{ ?circuit f1:country   ?circuitCountry }}
            OPTIONAL {{ ?circuit f1:circuitId ?circuitId      }}
          }}
        }}
    """)
    if not info_rows:
        return render(request, _COMING_SOON, {"page": "Race not found"})
    info = info_rows[0]

    wiki_rows = db.query(f"SELECT ?url WHERE {{ {uri} rdfs:seeAlso ?url . }} LIMIT 1")
    wiki_url  = wiki_rows[0]["url"] if wiki_rows else ""

    # Race results
    result_rows = db.query(f"""
        SELECT ?positionOrder ?grid ?laps ?time ?points
               ?driverLabel ?driverId ?constructorLabel WHERE {{
          ?res f1:resultId ?anyId ;
               f1:race {uri} ;
               f1:positionOrder ?positionOrder ;
               f1:driver ?driver ;
               f1:constructor ?constructor .
          OPTIONAL {{ ?res f1:grid   ?grid   }}
          OPTIONAL {{ ?res f1:laps   ?laps   }}
          OPTIONAL {{ ?res f1:time   ?time   }}
          OPTIONAL {{ ?res f1:points ?points }}
          ?driver rdfs:label ?driverLabel ;
                  f1:driverId ?driverId .
          ?constructor rdfs:label ?constructorLabel .
        }}
        ORDER BY ?positionOrder
    """)

    results = []
    for r in result_rows:
        results.append({
            "pos":               int(r.get("positionOrder", 99)),
            "grid":              r.get("grid", ""),
            "laps":              r.get("laps", ""),
            "time":              r.get("time", ""),
            "points":            r.get("points", ""),
            "driver_label":      r.get("driverLabel", ""),
            "driver_id":         r.get("driverId", ""),
            "constructor_label": r.get("constructorLabel", ""),
        })

    # Podium (p1, p2, p3 individually for template clarity)
    podium_map = {r["pos"]: r for r in results if r["pos"] <= 3}
    p1 = podium_map.get(1)
    p2 = podium_map.get(2)
    p3 = podium_map.get(3)

    entries    = len(results)
    total_laps = max((int(r["laps"]) for r in results if r["laps"]), default=0)

    # Fastest lap (highest speed = fastest)
    fl_rows = db.query(f"""
        SELECT ?driverLabel ?fastestLapTime WHERE {{
          ?res f1:resultId ?anyId ;
               f1:race {uri} ;
               f1:fastestLapSpeed ?speed ;
               f1:fastestLapTime  ?fastestLapTime ;
               f1:driver ?driver .
          ?driver rdfs:label ?driverLabel .
        }}
        ORDER BY DESC(?speed)
        LIMIT 1
    """)
    fastest = fl_rows[0] if fl_rows else {}

    # Qualifying
    qual_rows = db.query(f"""
        SELECT ?position ?driverLabel ?driverId ?constructorLabel ?q1 ?q2 ?q3 WHERE {{
          ?q f1:qualifyId ?anyId ;
             f1:race {uri} ;
             f1:position ?position ;
             f1:driver ?driver .
          OPTIONAL {{
            ?q f1:constructor ?ctor .
            ?ctor rdfs:label ?constructorLabel .
          }}
          OPTIONAL {{ ?q f1:q1 ?q1 }}
          OPTIONAL {{ ?q f1:q2 ?q2 }}
          OPTIONAL {{ ?q f1:q3 ?q3 }}
          ?driver rdfs:label ?driverLabel ;
                  f1:driverId ?driverId .
        }}
        ORDER BY ?position
    """)

    return render(request, "championship/race_detail.html", {
        "info":       info,
        "race_id":    race_id,
        "wiki_url":   wiki_url,
        "results":    results,
        "p1":         p1,
        "p2":         p2,
        "p3":         p3,
        "qualifying": qual_rows,
        "entries":    entries,
        "total_laps": total_laps,
        "fastest":    fastest,
    })


def circuits(request):
    db = GraphDBClient()

    # Basic circuit info — anchor on f1:circuitRef (unique to circuits.csv; circuitId
    # is also a literal on race entities so using it would return races too).
    rows = db.query("""
        SELECT ?uri ?label ?location ?country ?circuitId ?circuitRef WHERE {
          ?uri f1:circuitRef ?circuitRef ;
               rdfs:label ?label .
          OPTIONAL { ?uri f1:circuitId ?circuitId }
          OPTIONAL { ?uri f1:location  ?location  }
          OPTIONAL { ?uri f1:country   ?country   }
        }
    """)

    # Race stats per circuit — f1:circuit is the URI link property emitted only
    # from races.csv, so no need for an extra anchor predicate.
    stats: dict[str, dict] = {}
    for r in db.query("""
        SELECT ?circuit
               (COUNT(*)    AS ?races)
               (MIN(?year)  AS ?firstYear)
               (MAX(?year)  AS ?lastYear)
        WHERE {
          ?race f1:circuit ?circuit ;
                f1:year    ?year .
        } GROUP BY ?circuit
    """):
        stats[r["circuit"]] = {
            "races":      int(r["races"]),
            "first_year": r.get("firstYear", ""),
            "last_year":  r.get("lastYear",  ""),
        }

    all_circuits = []
    for r in rows:
        uri = r.get("uri", "")
        s   = stats.get(uri, {})
        all_circuits.append({
            "id":         r.get("circuitRef", "") or r.get("circuitId", ""),
            "circuit_id": r.get("circuitId", ""),
            "uri":        uri,
            "label":      r.get("label", ""),
            "location":   r.get("location", ""),
            "country":    r.get("country", ""),
            "races":      s.get("races", 0),
            "first_year": s.get("first_year", ""),
            "last_year":  s.get("last_year", ""),
        })

    # Determine active: last_year == max year in dataset
    max_year = max((c["last_year"] for c in all_circuits if c["last_year"]), default="0")
    for c in all_circuits:
        c["active"] = c["last_year"] == max_year

    # Podium sidebar — top 3 by race count
    podium = sorted(all_circuits, key=lambda c: c["races"], reverse=True)[:3]

    # Countries for filter
    countries = sorted({c["country"] for c in all_circuits if c["country"]})

    # Filtering
    q       = request.GET.get("q", "").strip()
    country = request.GET.get("country", "")
    status  = request.GET.get("status", "")   # "", "active", "inactive"
    filtered = all_circuits

    if q:
        ql = q.lower()
        filtered = [c for c in filtered if ql in c["label"].lower()
                    or ql in c["country"].lower()
                    or ql in c["location"].lower()]
    if country:
        filtered = [c for c in filtered if c["country"] == country]
    if status == "active":
        filtered = [c for c in filtered if c["active"]]
    elif status == "inactive":
        filtered = [c for c in filtered if not c["active"]]

    # Sorting
    sort  = request.GET.get("sort", "label")
    order = request.GET.get("order", "asc")
    key_map = {
        "label":      lambda c: c["label"].lower(),
        "country":    lambda c: c["country"].lower(),
        "races":      lambda c: c["races"],
        "first_year": lambda c: c["first_year"] or "0",
        "last_year":  lambda c: c["last_year"]  or "0",
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

    return render(request, "championship/circuits.html", {
        "circuits":    page_items,
        "podium":      podium,
        "countries":   countries,
        "q":           q,
        "country":     country,
        "status":      status,
        "sort":        sort,
        "order":       order,
        "page":        page,
        "total_pages": total_pages,
        "total":       total,
        "page_range":  page_range,
        "offset":      (page - 1) * per_page,
    })


def sparql(request):
    return render(request, _COMING_SOON, {"page": "SPARQL"})
