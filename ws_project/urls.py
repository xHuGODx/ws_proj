from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("championship.urls")),
]

handler404 = "championship.views.error_404"
handler500 = "championship.views.error_500"
