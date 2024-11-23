import os
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from Website import views as website_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', website_views.home_page, name='home'),
    path('login/', website_views.login_view, name='login'),
    path('logout/', website_views.logout_view, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'Website.views.handler404'
