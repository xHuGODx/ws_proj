from django.urls import path

from . import admin_views, views

app_name = "championship"

urlpatterns = [
    path("", views.home, name="home"),
    path("assistant/", views.llm_assistant, name="llm_assistant"),
    path("drivers/", views.drivers, name="drivers"),
    path("drivers/<str:driver_id>/", views.driver_detail, name="driver_detail"),
    path("constructors/", views.constructors, name="constructors"),
    path("constructors/<str:constructor_id>/", views.constructor_detail, name="constructor_detail"),
    path("seasons/", views.seasons, name="seasons"),
    path("seasons/<str:year>/", views.season_detail, name="season_detail"),
    path("races/", views.races, name="races"),
    path("races/<str:race_id>/", views.race_detail, name="race_detail"),
    path("circuits/", views.circuits, name="circuits"),
    path("circuits/<str:circuit_id>/", views.circuit_detail, name="circuit_detail"),
    path("sparql/", views.sparql, name="sparql"),

    # ── Admin ──────────────────────────────────────────────────────────────
    path("admin-panel/login/",   admin_views.admin_login,   name="admin_login"),
    path("admin-panel/logout/",  admin_views.admin_logout,  name="admin_logout"),
    path("admin-panel/",         admin_views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/imports/race-results/", admin_views.admin_race_results_import, name="admin_race_results_import"),
    path("admin-panel/imports/race-results/template.csv", admin_views.admin_results_import_template, name="admin_results_import_template"),
    path("admin-panel/imports/race-results/<str:token>/confirm/", admin_views.admin_race_results_import_confirm, name="admin_race_results_import_confirm"),
    path("admin-panel/operations/<int:batch_id>/rollback/", admin_views.admin_batch_rollback, name="admin_batch_rollback"),
    path("admin-panel/data-quality/", admin_views.admin_data_quality, name="admin_data_quality"),

    path("admin-panel/drivers/",                       admin_views.admin_drivers,        name="admin_drivers"),
    path("admin-panel/drivers/add/",                   admin_views.admin_driver_add,     name="admin_driver_add"),
    path("admin-panel/drivers/<str:driver_id>/edit/",  admin_views.admin_driver_edit,    name="admin_driver_edit"),
    path("admin-panel/drivers/<str:driver_id>/delete/",admin_views.admin_driver_delete,  name="admin_driver_delete"),

    path("admin-panel/constructors/",                             admin_views.admin_constructors,        name="admin_constructors"),
    path("admin-panel/constructors/add/",                         admin_views.admin_constructor_add,     name="admin_constructor_add"),
    path("admin-panel/constructors/<str:constructor_id>/edit/",   admin_views.admin_constructor_edit,    name="admin_constructor_edit"),
    path("admin-panel/constructors/<str:constructor_id>/delete/", admin_views.admin_constructor_delete,  name="admin_constructor_delete"),

    path("admin-panel/circuits/",                          admin_views.admin_circuits,        name="admin_circuits"),
    path("admin-panel/circuits/add/",                      admin_views.admin_circuit_add,     name="admin_circuit_add"),
    path("admin-panel/circuits/<str:circuit_id>/edit/",    admin_views.admin_circuit_edit,    name="admin_circuit_edit"),
    path("admin-panel/circuits/<str:circuit_id>/delete/",  admin_views.admin_circuit_delete,  name="admin_circuit_delete"),

    path("admin-panel/races/",                       admin_views.admin_races,        name="admin_races"),
    path("admin-panel/races/add/",                   admin_views.admin_race_add,     name="admin_race_add"),
    path("admin-panel/races/<str:race_id>/edit/",    admin_views.admin_race_edit,    name="admin_race_edit"),
    path("admin-panel/races/<str:race_id>/delete/",  admin_views.admin_race_delete,  name="admin_race_delete"),

    path("admin-panel/seasons/",                   admin_views.admin_seasons,        name="admin_seasons"),
    path("admin-panel/seasons/add/",               admin_views.admin_season_add,     name="admin_season_add"),
    path("admin-panel/seasons/<str:year>/edit/",   admin_views.admin_season_edit,    name="admin_season_edit"),
    path("admin-panel/seasons/<str:year>/delete/", admin_views.admin_season_delete,  name="admin_season_delete"),
]
