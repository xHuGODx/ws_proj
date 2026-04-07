from django.urls import path

from . import views

app_name = "championship"

urlpatterns = [
    path("", views.home, name="home"),
    path("drivers/", views.drivers, name="drivers"),
    path("drivers/<str:driver_id>/", views.driver_detail, name="driver_detail"),
    path("constructors/", views.constructors, name="constructors"),
    path("constructors/<str:constructor_id>/", views.constructor_detail, name="constructor_detail"),
    path("seasons/", views.seasons, name="seasons"),
    path("races/", views.races, name="races"),
    path("races/<str:race_id>/", views.race_detail, name="race_detail"),
    path("circuits/", views.circuits, name="circuits"),
    path("circuits/<str:circuit_id>/", views.circuit_detail, name="circuit_detail"),
    path("sparql/", views.sparql, name="sparql"),
]
