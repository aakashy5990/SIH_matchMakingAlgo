from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
from .utils import map_matching, reverse_geocode, create_map
from .models import RoadSegment

def home(request):
    return render(request, 'mapmatching/home.html')

def upload_view(request):
    if request.method == 'POST':
        gps_file = request.FILES.get('gps_file')
        road_file = request.FILES.get('road_file')
        
        if gps_file and road_file:
            gps_data = pd.read_csv(gps_file)
            road_segments = pd.read_csv(road_file)
            
            try:
                # Save road segments to the database
                road_segments_records = [
                    RoadSegment(start_latitude=row['start_latitude'], start_longitude=row['start_longitude'],
                                end_latitude=row['end_latitude'], end_longitude=row['end_longitude'], road_type=row['road_type'])
                    for index, row in road_segments.iterrows()
                ]
                RoadSegment.objects.bulk_create(road_segments_records)
                
                # Perform map matching
                matched_segments = map_matching(gps_data, road_segments)
                
                # Perform reverse geocoding for each matched segment
                for index, segment in matched_segments.iterrows():
                    city, state, normalized_city = reverse_geocode(segment['gps_lat'], segment['gps_lon'])
                    matched_segments.at[index, 'city'] = city
                    matched_segments.at[index, 'state'] = state
                    matched_segments.at[index, 'normalized_city'] = normalized_city
                
                # Create and save the map
                create_map(matched_segments)
                
                # Render results
                return render(request, 'mapmatching/results.html', {
                    'matched_segments': matched_segments.to_dict(orient='records'),
                    'map_html': 'map.html'
                })
            except KeyError as e:
                return HttpResponse(f"KeyError: {e}", status=400)
        else:
            return HttpResponse("Files are required.", status=400)

    return render(request, 'mapmatching/upload.html')