from django.urls import path
from .views import (
    NotificationListCreateView,
    NotificationDeleteView,
    NotificationTemplateListCreateView,
    NotificationTemplateDetailView,
)


urlpatterns = [
    path("", NotificationListCreateView.as_view()),
    path("<int:pk>/", NotificationDeleteView.as_view()),
    path("templates/", NotificationTemplateListCreateView.as_view()),
    path("templates/<int:pk>/", NotificationTemplateDetailView.as_view()),
]