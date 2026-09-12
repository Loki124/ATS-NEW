from django.urls import path

from .views import (
    StandardResumeConfigView,
    CandidateTableConfigView,
    RegistrationFormListView,
    RegistrationFormDetailView,
)

urlpatterns = [
    path('', StandardResumeConfigView.as_view()),
    # 登记 / 申请表（多套）
    path('application-form/', RegistrationFormListView.as_view()),
    path('application-form/<int:pk>/', RegistrationFormDetailView.as_view()),
    # 候选人信息登记表设置（单体 config）
    path('candidate-info-table/', CandidateTableConfigView.as_view()),
]
