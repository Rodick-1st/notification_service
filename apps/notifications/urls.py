from django.urls import path
from .views import NotificationListCreateView, NotificationDeleteView


urlpatterns = [
    path("", NotificationListCreateView.as_view()),
    path("<int:pk>/", NotificationDeleteView.as_view()),
]