from django.urls import path

from .views import home

app_name = "championship"

urlpatterns = [
    path("", home, name="home"),
]

