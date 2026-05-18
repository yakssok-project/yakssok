from django.urls import path

from . import views

urlpatterns = [
    path('', views.pharmacy_map_view, name='pharmacy_map'),
    path('api/nearby/', views.nearby_pharmacies_api, name='pharmacy_nearby_api'),
]
