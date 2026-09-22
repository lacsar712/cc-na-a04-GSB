from django.urls import path

from inspection import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.list_view, name="list"),
    path("inspections/new/", views.create_view, name="create"),
    path("inspections/<int:pk>/", views.detail_view, name="detail"),
    path("chains/", views.chain_index_view, name="chains"),
    path("chains/<str:aid_code>/", views.chain_view, name="chain"),
    path("events/", views.events_view, name="events"),
    path("settings/threshold/", views.threshold_view, name="threshold"),
]
