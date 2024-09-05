from django.contrib import admin
from django.urls import path, include
from mapmatching_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views. home, name='home'),  # Add a home view
    path('upload/', include('mapmatching_app.urls')),  # Include mapmatching_app URLs
]
