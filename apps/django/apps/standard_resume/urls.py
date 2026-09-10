from django.urls import path

from .views import (
    StandardResumeConfigView,
    ApplicationFormConfigView,
    CandidateTableConfigView,
)

urlpatterns = [
    path('', StandardResumeConfigView.as_view()),
    path('application-form/', ApplicationFormConfigView.as_view()),
    path('candidate-info-table/', CandidateTableConfigView.as_view()),
]
