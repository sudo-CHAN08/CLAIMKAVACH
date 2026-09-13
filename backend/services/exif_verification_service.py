import math
import subprocess
import json
import re
import os
import tempfile
import requests
from typing import Dict, Any, Tuple, Optional

class VideoEXIFVerificationService:
    def __init__(self, max_allowed_distance_meters: float = 150.0):
        self.max_allowed_distance_meters = max_allowed_distance_meters

    def extract_metadata_from_url(self, file_url: str) -> Dict[str, Any]:
        """Downloads media from a public URL to a temp file and extracts metadata."""
        try:
            res = requests.get(file_url, stream=True, timeout=10)
            res.raise_for_status()

            ext = ".mp4" if "video" in res.headers.get("content-type", "") else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                for chunk in res.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                return self.extract_video_metadata(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            return {"has_gps": False, "error": f"URL Fetch Error: {str(e)}", "latitude": None, "longitude": None}

    def extract_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extracts EXIF/GPS metadata using ffprobe."""
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            format_tags = data.get("format", {}).get("tags", {})

            location_raw = format_tags.get("location") or format_tags.get("com.apple.quicktime.location.ISO6709")
            creation_time = format_tags.get("creation_time")
            latitude, longitude = self._parse_iso6709(location_raw) if location_raw else (None, None)

            return {
                "has_gps": latitude is not None and longitude is not None,
                "latitude": latitude,
                "longitude": longitude,
                "creation_time": creation_time,
                "raw_tags": format_tags
            }
        except Exception as e:
            return {"has_gps": False, "error": str(e), "latitude": None, "longitude": None}

    def verify_video_against_plot(self, video_path: str, plot_spatial_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self.extract_video_metadata(video_path)
        if not metadata.get("has_gps"):
            return {"verified": False, "reason": "NO_GPS_METADATA", "metadata": metadata}

        video_lat, video_lng = metadata["latitude"], metadata["longitude"]
        centroid = plot_spatial_data.get("centroid", {})
        plot_lat, plot_lng = centroid.get("latitude"), centroid.get("longitude")

        if plot_lat is None or plot_lng is None:
            return {"verified": False, "reason": "INVALID_PLOT_COORDINATES", "metadata": metadata}

        distance = self._haversine_distance(video_lat, video_lng, plot_lat, plot_lng)
        is_valid = distance <= self.max_allowed_distance_meters

        return {
            "verified": is_valid,
            "reason": "MATCH_SUCCESS" if is_valid else "LOCATION_MISMATCH",
            "distance_meters": round(distance, 2),
            "threshold_meters": self.max_allowed_distance_meters,
            "video_coordinates": {"latitude": video_lat, "longitude": video_lng},
            "plot_centroid": {"latitude": plot_lat, "longitude": plot_lng}
        }

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0
        dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _parse_iso6709(iso_str: str) -> Tuple[Optional[float], Optional[float]]:
        try:
            match = re.match(r'([+-]\d+\.\d+)([+-]\d+\.\d+)', iso_str)
            if match:
                return float(match.group(1)), float(match.group(2))
        except Exception:
            pass
        return None, None