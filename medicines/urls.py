from django.urls import path

from . import views

urlpatterns = [
    path('', views.medicine_list_view, name='medicine_list'),
    path('<int:pk>/', views.medicine_detail_view, name='medicine_detail'),
]
