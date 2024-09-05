from django.db import models

class RoadSegment(models.Model):
    start_latitude = models.FloatField()
    start_longitude = models.FloatField()
    end_latitude = models.FloatField()
    end_longitude = models.FloatField()
    road_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.road_type} from ({self.start_latitude}, {self.start_longitude}) to ({self.end_latitude}, {self.end_longitude})"