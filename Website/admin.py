from django.contrib import admin

from .models import *

admin.site.register(Raspberry)
admin.site.register(Group)
admin.site.register(SensorData)
admin.site.register(SensorLocation)
admin.site.register(Plant)
admin.site.register(Action)
admin.site.register(DataPayload)
admin.site.register(UserGroup)