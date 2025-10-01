"""
Geolocation utilities for tracking test locations
"""
import requests
from typing import Dict, Optional
import json
import streamlit as st
from streamlit.components.v1 import html

class GeolocationService:
    """Service to get geolocation information"""
    
    def __init__(self):
        self.cache = {}
        self.user_location_fetched = False
    
    def get_user_location_client_side(self):
        """
        Fetch user's location from their browser using client-side JavaScript.
        This runs in the user's browser and gets their actual location.
        """
        if 'user_location' not in st.session_state:
            st.session_state.user_location = None
        
        # JavaScript code to fetch location from user's browser
        location_script = """
        <script>
        // Fetch user location from their browser
        fetch('https://ipapi.co/json/')
            .then(response => response.json())
            .then(data => {
                // Send data back to Streamlit
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        country: data.country_name || 'Unknown',
                        country_code: data.country_code || 'XX',
                        city: data.city || 'Unknown',
                        region: data.region || 'Unknown',
                        latitude: String(data.latitude || 0),
                        longitude: String(data.longitude || 0),
                        timezone: data.timezone || 'UTC',
                        ip: data.ip || 'Unknown'
                    }
                }, '*');
            })
            .catch(error => {
                console.error('Geolocation failed:', error);
                // Fallback to another service
                fetch('http://ip-api.com/json/')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            window.parent.postMessage({
                                type: 'streamlit:setComponentValue',
                                value: {
                                    country: data.country || 'Unknown',
                                    country_code: data.countryCode || 'XX',
                                    city: data.city || 'Unknown',
                                    region: data.regionName || 'Unknown',
                                    latitude: String(data.lat || 0),
                                    longitude: String(data.lon || 0),
                                    timezone: data.timezone || 'UTC',
                                    ip: data.query || 'Unknown'
                                }
                            }, '*');
                        }
                    });
            });
        </script>
        """
        
        # Render the component (hidden, just for fetching location)
        result = html(location_script, height=0)
        
        if result:
            st.session_state.user_location = result
            self.cache['location'] = result
            return result
        
        return None
    
    def get_location(self, force_refresh: bool = False, use_client_side: bool = True) -> Dict[str, str]:
        """
        Get current geolocation.
        
        Args:
            force_refresh: Force refresh the location
            use_client_side: If True, tries to get user's actual location from their browser
        """
        
        # Try to get user's location from session state (client-side)
        if use_client_side and 'user_location' in st.session_state and st.session_state.user_location:
            return st.session_state.user_location
        
        # Check cache first (unless forced refresh)
        if not force_refresh and 'location' in self.cache:
            return self.cache['location']
        
        # Try multiple geolocation services in order
        location = None
        
        # Service 1: ipapi.co (reliable, no key needed)
        try:
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('country_name') and data.get('country_name') != 'Unknown':
                    location = {
                        'country': data.get('country_name', 'Unknown'),
                        'country_code': data.get('country_code', 'XX'),
                        'region': data.get('region', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': str(data.get('latitude', 0)),
                        'longitude': str(data.get('longitude', 0)),
                        'timezone': data.get('timezone', 'UTC'),
                        'ip': data.get('ip', 'Unknown')
                    }
                    self.cache['location'] = location
                    return location
        except Exception as e:
            print(f"ipapi.co failed: {e}")
        
        # Service 2: ip-api.com (backup, free)
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('country'):
                    location = {
                        'country': data.get('country', 'Unknown'),
                        'country_code': data.get('countryCode', 'XX'),
                        'region': data.get('regionName', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': str(data.get('lat', 0)),
                        'longitude': str(data.get('lon', 0)),
                        'timezone': data.get('timezone', 'UTC'),
                        'ip': data.get('query', 'Unknown')
                    }
                    self.cache['location'] = location
                    return location
        except Exception as e:
            print(f"ip-api.com failed: {e}")
        
        # Service 3: ipinfo.io (another backup)
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('country'):
                    # Parse location string like "37.7749,-122.4194"
                    loc_parts = data.get('loc', '0,0').split(',')
                    location = {
                        'country': data.get('country', 'Unknown'),
                        'country_code': data.get('country', 'XX'),
                        'region': data.get('region', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': loc_parts[0] if len(loc_parts) > 0 else '0',
                        'longitude': loc_parts[1] if len(loc_parts) > 1 else '0',
                        'timezone': data.get('timezone', 'UTC'),
                        'ip': data.get('ip', 'Unknown')
                    }
                    self.cache['location'] = location
                    return location
        except Exception as e:
            print(f"ipinfo.io failed: {e}")
        
        # Return default if all services fail
        return {
            'country': 'Unknown',
            'country_code': 'XX',
            'region': 'Unknown',
            'city': 'Unknown',
            'latitude': '0',
            'longitude': '0',
            'timezone': 'UTC',
            'ip': 'Unknown'
        }
    
    def get_location_string(self) -> str:
        """Get location as a formatted string"""
        location = self.get_location()
        
        parts = []
        if location['city'] != 'Unknown':
            parts.append(location['city'])
        if location['region'] != 'Unknown' and location['region'] != location['city']:
            parts.append(location['region'])
        if location['country'] != 'Unknown':
            parts.append(location['country'])
        
        if parts:
            return ', '.join(parts)
        return 'Unknown'
    
    def get_country_flag(self, country_code: str = None) -> str:
        """Get country flag emoji from country code"""
        if country_code is None:
            location = self.get_location()
            country_code = location['country_code']
        
        if country_code == 'XX' or country_code == 'Unknown':
            return '🌍'
        
        # Convert country code to flag emoji
        # Each letter is converted to its regional indicator symbol
        try:
            flag = ''.join(chr(ord(c) + 127397) for c in country_code.upper())
            return flag
        except:
            return '🌍'

# Global instance
geo_service = GeolocationService()

