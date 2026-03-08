# reports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("generate-csv/", views.generate_report_and_download_csv, name="generate_report_csv"),
]
