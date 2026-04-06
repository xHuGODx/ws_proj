from django.urls import path

from . import views

app_name = "championship"

urlpatterns = [
    path("", views.home, name="home"),
    path("drivers/", views.drivers, name="drivers"),
    path("constructors/", views.constructors, name="constructors"),
    path("seasons/", views.seasons, name="seasons"),
    path("races/", views.races, name="races"),
    path("circuits/", views.circuits, name="circuits"),
    path("sparql/", views.sparql, name="sparql"),
]
