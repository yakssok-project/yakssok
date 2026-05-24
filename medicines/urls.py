from django.urls import path

from . import views

urlpatterns = [
    path('', views.medicine_list_view, name='medicine_list'),
    path('<int:pk>/', views.medicine_detail_view, name='medicine_detail'),
    path("prescription/upload/", views.prescription_upload, name="prescription_upload"),
    path("prescription/camera/", views.prescription_camera, name="prescription_camera"),
    path("prescription/result/", views.prescription_result, name="prescription_result"),
    path("prescription/preview/", views.prescription_preview, name="prescription_preview"),
    path("prescription/loading/", views.prescription_loading, name="prescription_loading"),
    path("medicine/search-add/", views.medicine_search_add, name="medicine_search_add"),
    path("medicine/search-select/", views.medicine_search_select, name="medicine_search_select"),
    path("medicine/edit-temp/<int:index>/", views.medicine_edit_temp, name="medicine_edit_temp"),
    path("prescription/save/", views.prescription_save, name="prescription_save"),
    path("reminder/", views.medication_reminder_view, name="medication_reminder"),
]
