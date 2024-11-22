import os
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from Website import views as website_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', website_views.home_page, name='home_page'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'Website.views.handler404'