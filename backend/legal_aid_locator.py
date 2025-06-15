import requests
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import math

class LegalAidLocator:
    def __init__(self):
        # Karnataka legal aid centers database
        self.legal_aid_centers = [
            {
                "id": 1,
                "name": "Karnataka State Legal Services Authority",
                "address": "High Court Building, Bangalore",
                "phone": "+91-80-22217735",
                "email": "kslsa@karnataka.gov.in",
                "type": "state_authority",
                "services": ["civil", "criminal", "family", "consumer", "labor"],
                "coordinates": {"lat": 12.9716, "lng": 77.5946},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english", "hindi"],
                "free_services": True,
                "rating": 4.2
            },
            {
                "id": 2,
                "name": "Bangalore Urban District Legal Services Authority",
                "address": "City Civil Court Complex, Bangalore",
                "phone": "+91-80-22867890",
                "email": "dlsa.bangalore@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "property"],
                "coordinates": {"lat": 12.9762, "lng": 77.6033},
                "timings": "10:00 AM - 5:00 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.0
            },
            {
                "id": 3,
                "name": "Mysore District Legal Services Authority",
                "address": "District Court Complex, Mysore",
                "phone": "+91-821-2425789",
                "email": "dlsa.mysore@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "consumer"],
                "coordinates": {"lat": 12.2958, "lng": 76.6394},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.1
            },
            {
                "id": 4,
                "name": "Hubli-Dharwad Legal Aid Center",
                "address": "District Court, Hubli",
                "phone": "+91-836-2235467",
                "email": "dlsa.hubli@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "labor"],
                "coordinates": {"lat": 15.3647, "lng": 75.1240},
                "timings": "10:00 AM - 5:00 PM",
                "languages": ["kannada", "english", "marathi"],
                "free_services": True,
                "rating": 3.9
            },
            {
                "id": 5,
                "name": "Mangalore Legal Aid Society",
                "address": "Court Road, Mangalore",
                "phone": "+91-824-2441234",
                "email": "las.mangalore@karnataka.gov.in",
                "type": "legal_aid_society",
                "services": ["civil", "criminal", "family", "consumer", "maritime"],
                "coordinates": {"lat": 12.9141, "lng": 74.8560},
                "timings": "9:00 AM - 6:00 PM",
                "languages": ["kannada", "english", "tulu", "konkani"],
                "free_services": True,
                "rating": 4.3
            },
            {
                "id": 6,
                "name": "Gulbarga District Legal Services",
                "address": "District Court Complex, Gulbarga",
                "phone": "+91-8472-225678",
                "email": "dlsa.gulbarga@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "property"],
                "coordinates": {"lat": 17.3297, "lng": 76.8343},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english", "urdu"],
                "free_services": True,
                "rating": 3.8
            },
            {
                "id": 7,
                "name": "Bellary Legal Aid Center",
                "address": "Court Complex, Bellary",
                "phone": "+91-8392-245789",
                "email": "dlsa.bellary@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "mining"],
                "coordinates": {"lat": 15.1394, "lng": 76.9214},
                "timings": "10:00 AM - 5:00 PM",
                "languages": ["kannada", "english", "telugu"],
                "free_services": True,
                "rating": 3.7
            },
            {
                "id": 8,
                "name": "Shimoga District Legal Services",
                "address": "District Court, Shimoga",
                "phone": "+91-8182-225890",
                "email": "dlsa.shimoga@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "environmental"],
                "coordinates": {"lat": 13.9299, "lng": 75.5681},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.0
            },
            {
                "id": 9,
                "name": "Tumkur Legal Aid Society",
                "address": "Court Road, Tumkur",
                "phone": "+91-816-2274567",
                "email": "las.tumkur@karnataka.gov.in",
                "type": "legal_aid_society",
                "services": ["civil", "criminal", "family", "agricultural"],
                "coordinates": {"lat": 13.3379, "lng": 77.1022},
                "timings": "9:00 AM - 5:00 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 3.9
            },
            {
                "id": 10,
                "name": "Hassan District Legal Services",
                "address": "District Court Complex, Hassan",
                "phone": "+91-8172-268901",
                "email": "dlsa.hassan@karnataka.gov.in",
                "type": "district_authority",
                "services": ["civil", "criminal", "family", "property"],
                "coordinates": {"lat": 13.0072, "lng": 76.0962},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.1
            }
        ]
        
        # Private legal aid organizations
        self.private_legal_aid = [
            {
                "id": 11,
                "name": "Alternative Law Forum",
                "address": "Shantinagar, Bangalore",
                "phone": "+91-80-25457659",
                "email": "info@altlawforum.org",
                "type": "ngo",
                "services": ["human_rights", "environmental", "labor", "women_rights"],
                "coordinates": {"lat": 12.9698, "lng": 77.6124},
                "timings": "10:00 AM - 6:00 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.5
            },
            {
                "id": 12,
                "name": "Janaagraha Legal Aid",
                "address": "Indiranagar, Bangalore",
                "phone": "+91-80-25834455",
                "email": "legal@janaagraha.org",
                "type": "ngo",
                "services": ["civic", "consumer", "property", "governance"],
                "coordinates": {"lat": 12.9784, "lng": 77.6408},
                "timings": "9:00 AM - 6:00 PM",
                "languages": ["kannada", "english"],
                "free_services": True,
                "rating": 4.4
            },
            {
                "id": 13,
                "name": "Women's Legal Aid Centre",
                "address": "Jayanagar, Bangalore",
                "phone": "+91-80-26633789",
                "email": "help@womenslegal.org",
                "type": "ngo",
                "services": ["family", "domestic_violence", "women_rights", "child_custody"],
                "coordinates": {"lat": 12.9279, "lng": 77.5937},
                "timings": "9:30 AM - 5:30 PM",
                "languages": ["kannada", "english", "hindi"],
                "free_services": True,
                "rating": 4.6
            }
        ]
        
        # Combine all legal aid centers
        self.all_centers = self.legal_aid_centers + self.private_legal_aid

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def get_coordinates(self, location: str) -> Optional[Dict]:
        """Get coordinates for a location using geocoding"""
        try:
            # For demo purposes, return coordinates for major Karnataka cities
            city_coordinates = {
                "bangalore": {"lat": 12.9716, "lng": 77.5946},
                "bengaluru": {"lat": 12.9716, "lng": 77.5946},
                "mysore": {"lat": 12.2958, "lng": 76.6394},
                "mysuru": {"lat": 12.2958, "lng": 76.6394},
                "hubli": {"lat": 15.3647, "lng": 75.1240},
                "dharwad": {"lat": 15.4589, "lng": 75.0078},
                "mangalore": {"lat": 12.9141, "lng": 74.8560},
                "gulbarga": {"lat": 17.3297, "lng": 76.8343},
                "bellary": {"lat": 15.1394, "lng": 76.9214},
                "shimoga": {"lat": 13.9299, "lng": 75.5681},
                "tumkur": {"lat": 13.3379, "lng": 77.1022},
                "hassan": {"lat": 13.0072, "lng": 76.0962},
                "davangere": {"lat": 14.4644, "lng": 75.9218},
                "bijapur": {"lat": 16.8302, "lng": 75.7100},
                "raichur": {"lat": 16.2120, "lng": 77.3439}
            }
            
            location_lower = location.lower().strip()
            
            # Check if location matches any known city
            for city, coords in city_coordinates.items():
                if city in location_lower:
                    return coords
            
            # If no match found, return Bangalore coordinates as default
            return city_coordinates["bangalore"]
            
        except Exception as e:
            print(f"Error getting coordinates: {e}")
            return {"lat": 12.9716, "lng": 77.5946}  # Default to Bangalore

    def search_nearby_legal_aid(self, location: str, legal_type: str = "general", radius: int = 50) -> List[Dict]:
        """Search for nearby legal aid centers"""
        try:
            # Get coordinates for the search location
            search_coords = self.get_coordinates(location)
            if not search_coords:
                return []
            
            search_lat = search_coords["lat"]
            search_lng = search_coords["lng"]
            
            # Filter and sort centers by distance
            nearby_centers = []
            
            for center in self.all_centers:
                center_lat = center["coordinates"]["lat"]
                center_lng = center["coordinates"]["lng"]
                
                # Calculate distance
                distance = self.calculate_distance(search_lat, search_lng, center_lat, center_lng)
                
                # Check if within radius
                if distance <= radius:
                    # Check if center provides the requested legal service
                    if legal_type == "general" or legal_type in center.get("services", []):
                        center_copy = center.copy()
                        center_copy["distance"] = round(distance, 2)
                        center_copy["estimated_travel_time"] = self.estimate_travel_time(distance)
                        nearby_centers.append(center_copy)
            
            # Sort by distance
            nearby_centers.sort(key=lambda x: x["distance"])
            
            return nearby_centers
            
        except Exception as e:
            print(f"Error searching legal aid centers: {e}")
            return []

    def estimate_travel_time(self, distance_km: float) -> str:
        """Estimate travel time based on distance"""
        # Assume average speed of 30 km/h in city traffic
        time_hours = distance_km / 30
        time_minutes = int(time_hours * 60)
        
        if time_minutes < 60:
            return f"{time_minutes} minutes"
        else:
            hours = time_minutes // 60
            minutes = time_minutes % 60
            if minutes > 0:
                return f"{hours} hour {minutes} minutes"
            else:
                return f"{hours} hour"

    def get_directions(self, start_location: str, end_location: str) -> Dict:
        """Get directions between two locations"""
        try:
            start_coords = self.get_coordinates(start_location)
            end_coords = self.get_coordinates(end_location)
            
            if not start_coords or not end_coords:
                return {"error": "Could not find coordinates for locations"}
            
            # Calculate distance and estimated time
            distance = self.calculate_distance(
                start_coords["lat"], start_coords["lng"],
                end_coords["lat"], end_coords["lng"]
            )
            
            # Generate basic directions (simplified)
            directions = {
                "start_location": start_location,
                "end_location": end_location,
                "start_coordinates": start_coords,
                "end_coordinates": end_coords,
                "distance_km": round(distance, 2),
                "estimated_time": self.estimate_travel_time(distance),
                "steps": [
                    f"Start from {start_location}",
                    f"Head towards {end_location}",
                    f"Continue for {round(distance, 1)} km",
                    f"Arrive at {end_location}"
                ],
                "map_url": f"https://www.google.com/maps/dir/{start_coords['lat']},{start_coords['lng']}/{end_coords['lat']},{end_coords['lng']}"
            }
            
            return directions
            
        except Exception as e:
            print(f"Error getting directions: {e}")
            return {"error": str(e)}

    def get_center_details(self, center_id: int) -> Optional[Dict]:
        """Get detailed information about a specific legal aid center"""
        try:
            for center in self.all_centers:
                if center["id"] == center_id:
                    return center
            return None
        except Exception as e:
            print(f"Error getting center details: {e}")
            return None

    def search_by_service_type(self, service_type: str) -> List[Dict]:
        """Search legal aid centers by specific service type"""
        try:
            matching_centers = []
            
            for center in self.all_centers:
                if service_type in center.get("services", []):
                    matching_centers.append(center)
            
            # Sort by rating
            matching_centers.sort(key=lambda x: x.get("rating", 0), reverse=True)
            
            return matching_centers
            
        except Exception as e:
            print(f"Error searching by service type: {e}")
            return []

    def get_emergency_contacts(self) -> List[Dict]:
        """Get emergency legal aid contacts"""
        emergency_contacts = [
            {
                "name": "Karnataka State Legal Services Authority - Emergency",
                "phone": "+91-80-22217735",
                "email": "emergency@kslsa.karnataka.gov.in",
                "available": "24/7",
                "services": ["emergency_legal_aid", "bail_assistance", "urgent_consultation"]
            },
            {
                "name": "Women Helpline - Legal Support",
                "phone": "1091",
                "email": "women.helpline@karnataka.gov.in",
                "available": "24/7",
                "services": ["domestic_violence", "women_rights", "emergency_protection"]
            },
            {
                "name": "Child Helpline - Legal Aid",
                "phone": "1098",
                "email": "child.helpline@karnataka.gov.in",
                "available": "24/7",
                "services": ["child_protection", "custody_issues", "child_abuse"]
            },
            {
                "name": "Senior Citizen Helpline",
                "phone": "14567",
                "email": "senior.helpline@karnataka.gov.in",
                "available": "9 AM - 6 PM",
                "services": ["elder_abuse", "property_disputes", "pension_issues"]
            }
        ]
        
        return emergency_contacts

    def save_search_history(self, search_data: Dict) -> bool:
        """Save search history for offline access"""
        try:
            history_file = "cache/search_history.json"
            
            # Load existing history
            history = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Add new search with timestamp
            search_data["timestamp"] = datetime.now().isoformat()
            history.append(search_data)
            
            # Keep only last 50 searches
            history = history[-50:]
            
            # Save updated history
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving search history: {e}")
            return False

    def get_search_history(self) -> List[Dict]:
        """Get saved search history"""
        try:
            history_file = "cache/search_history.json"
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return []
            
        except Exception as e:
            print(f"Error getting search history: {e}")
            return []
