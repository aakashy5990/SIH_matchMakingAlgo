from django.contrib import admin
from .models import RoadSegment
# Register your models here.
@admin.register(RoadSegment)
class RoadSegmentModelAdmin(admin.ModelAdmin):
    list_display = ['start_latitude','start_longitude','end_latitude','end_longitude','road_type']