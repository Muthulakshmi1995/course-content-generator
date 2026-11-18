
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("", views.student_dashboard, name="student_dashboard"),
    path("generate/", views.generate_content, name="generate_content"),
    path("topic/<int:topic_id>/", views.view_content, name="view_content"),
    path("topic/<int:topic_id>/submit-quiz/", views.submit_quiz, name="submit_quiz"),
    path("topic/<int:topic_id>/export-pdf/", views.export_pdf, name="export_pdf"),
]
