import os
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from Website import views as website_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', website_views.home_page, name='home'),
    path('graphs/<int:id>/', website_views.graph_page, name='raspberry_detail'),
    path('raspberry/update/<int:id>/', website_views.raspberry_update, name='raspberry_update'),
    path('raspberry/delete/<int:id>/', website_views.raspberry_delete, name='raspberry_delete'),
    path('login/', website_views.login_view, name='login'),
    path('logout/', website_views.logout_view, name='logout'),
    path('api/sensor-data/', website_views.receive_sensor_data, name='receive_sensor_data'),
    path('api/sensor-data/<int:raspberry_id>/', website_views.get_latest_sensor_data, name='get_latest_sensor_data'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'Website.views.handler404'
