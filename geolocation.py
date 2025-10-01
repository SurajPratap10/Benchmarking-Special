"""
Geolocation utilities for tracking test locations
"""
import requests
from typing import Dict, Optional
import json
import streamlit as st

class GeolocationService:
    """Service to get geolocation information"""
    
    def __init__(self):
        self.cache = {}
    
    def _get_client_ip(self) -> Optional[str]:
        """
        Try to get the client's real IP address from Streamlit headers.
        This works when deployed on Streamlit Cloud.
        """
        try:
            # Try to get from Streamlit context (when deployed)
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()
            if ctx and hasattr(ctx, 'session_id'):
                # Try to get session info
                session_info = st.runtime.get_instance()._session_mgr.get_session_info(ctx.session_id)
                if session_info and hasattr(session_info, 'client'):
                    return session_info.client.request.remote_ip
        except:
            pass
        
        # Fallback: check if we're running locally or on server
        # When on Streamlit Cloud, the headers might have X-Forwarded-For
        try:
            import streamlit.web.server.websocket_headers as wsh
            headers = wsh.get_websocket_headers()
            if headers and 'X-Forwarded-For' in headers:
                return headers['X-Forwarded-For'].split(',')[0].strip()
        except:
            pass
        
        return None
    
    def get_location(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Get current geolocation based on client IP address
        Uses ipapi.co for geolocation (free, no API key needed)
        """
        
        # Check cache first (unless forced refresh)
        if not force_refresh and 'location' in self.cache:
            return self.cache['location']
        
        # Try to get client IP first
        client_ip = self._get_client_ip()
        
        try:
            # If we have client IP, use it. Otherwise, ipapi.co will use the requester's IP
            if client_ip:
                response = requests.get(f'https://ipapi.co/{client_ip}/json/', timeout=3)
            else:
                # This will get server IP when running on Streamlit Cloud without client IP
                response = requests.get('https://ipapi.co/json/', timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
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
                
                # Cache the result
                self.cache['location'] = location
                return location
        
        except Exception as e:
            print(f"Primary geolocation service failed: {e}")
        
        # Fallback to ip-api.com (free, no API key)
        try:
            if client_ip:
                response = requests.get(f'http://ip-api.com/json/{client_ip}', timeout=3)
            else:
                response = requests.get('http://ip-api.com/json/', timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
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
                
                # Cache the result
                self.cache['location'] = location
                return location
        
        except Exception as e:
            print(f"Fallback geolocation service failed: {e}")
        
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

