import pandas as pd
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
import folium
import os
import requests
import logging
from django.conf import settings
from geopy.distance import geodesic

def map_matching(gps_data: pd.DataFrame, road_segments: pd.DataFrame):
    required_columns = ['start_latitude', 'start_longitude', 'end_latitude', 'end_longitude', 'road_type']
    
    for col in required_columns:
        if col not in road_segments.columns:
            raise KeyError(f"Required column '{col}' not found in road_segments")

    # Create a BallTree for road segments
    road_array = road_segments[['start_latitude', 'start_longitude', 'end_latitude', 'end_longitude']].to_numpy()
    tree = BallTree(road_array[:, :2])  # Use start_latitude and start_longitude for querying

    matched_segments = []
    geolocator = Nominatim(user_agent="map-matching")

    for index, gps_row in gps_data.iterrows():
        gps_lat = gps_row['latitude']
        gps_lon = gps_row['longitude']
        timestamp = gps_row['timestamp']

        # Calculate distance and speed if it's not the first point
        if index > 0:
            previous_row = gps_data.iloc[index - 1]
            previous_lat = previous_row['latitude']
            previous_lon = previous_row['longitude']
            previous_timestamp = previous_row['timestamp']
            
            # Calculate distance using geodesic distance
            distance = geodesic((previous_lat, previous_lon), (gps_lat, gps_lon)).meters
            
            # Calculate time difference in seconds
            time_diff = (pd.to_datetime(timestamp) - pd.to_datetime(previous_timestamp)).total_seconds()
            
            # Calculate speed in meters per second
            if time_diff > 0:
                speed = distance / time_diff
            else:
                speed = 0.0
        else:
            distance = 0.0
            speed = 0.0

        # Determine k based on the number of available road segments
        k = 5
        if len(road_segments) < k:
            k = len(road_segments)

        # Find the nearest road segments
        dist, ind = tree.query([[gps_lat, gps_lon]], k=k)  # Adjusted k based on the number of road segments
        nearest_segments = road_segments.iloc[ind[0]]

        # Initialize variables for the best match
        best_segment = None
        best_score = float('inf')

        # Score each nearby segment based on distance, speed, and road type
        for _, segment in nearest_segments.iterrows():
            segment_lat = (segment['start_latitude'] + segment['end_latitude']) / 2
            segment_lon = (segment['start_longitude'] + segment['end_longitude']) / 2

            # Calculate the distance from the GPS point to the segment center
            segment_center = (segment_lat, segment_lon)
            gps_point = (gps_lat, gps_lon)
            segment_distance = geodesic(segment_center, gps_point).meters

            # Calculate a score considering distance and road type
            score = segment_distance
            if speed > 50:  # Example threshold for high speed (could be adjusted)
                # vehical on haiway if speed is greater than 50m 
                if segment['road_type'] == 'highway':
                    score -= 10  # Bonus for matching road type
            else:
                if segment['road_type'] == 'service road':
                    score -= 10  # Bonus for matching road type

            # Select the best segment based on the score
            if score < best_score:
                best_score = score
                best_segment = segment

        # Reverse geocode to get location name
        location = geolocator.reverse((gps_lat, gps_lon), exactly_one=True)
        address = location.raw.get('address', {})
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')

        matched_segments.append({
            'gps_lat': gps_lat,
            'gps_lon': gps_lon,
            'timestamp': timestamp,
            'start_lat': best_segment['start_latitude'],
            'start_lon': best_segment['start_longitude'],
            'end_lat': best_segment['end_latitude'],
            'end_lon': best_segment['end_longitude'],
            'distance_m': distance,
            'speed_mps': speed,
            'city': city,
            'state': state,
            'country': country,
            'road_type': best_segment['road_type']  # Add road type to the results
        })
    
    matched_segments_df = pd.DataFrame(matched_segments)
    return matched_segments_df


def reverse_geocode(lat, lon):
    api_key = 'b0534b2739234881ba860d54a6b4db19'  # Replace with your OpenCage API key
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if data['results']:
        components = data['results'][0]['components']
        city = components.get('city', 'Unknown')
        state = components.get('state', 'Unknown')
        normalized_city = components.get('_normalized_city', 'Unknown')
        return city, state, normalized_city
    else:
        return None, None, None

logger = logging.getLogger(__name__)

def create_map(matched_segments: pd.DataFrame):
    # Create a Folium map centered around the mean of the GPS data
    map_center = [matched_segments['gps_lat'].mean(), matched_segments['gps_lon'].mean()]
    map_obj = folium.Map(location=map_center, zoom_start=13)
    
    # Add a polyline to the map
    path_coordinates = matched_segments[['gps_lat', 'gps_lon']].values.tolist()
    folium.PolyLine(path_coordinates, color="blue", weight=5).add_to(map_obj)
    
    # Save the map to an HTML file in the static directory
    static_dir = os.path.join(settings.BASE_DIR, 'static')
    os.makedirs(static_dir, exist_ok=True)
    map_html_path = os.path.join(static_dir, 'map.html')
    
    logger.info(f'Saving map to {map_html_path}')
    map_obj.save(map_html_path)