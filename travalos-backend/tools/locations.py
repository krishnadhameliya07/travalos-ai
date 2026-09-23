import math
from typing import Dict, Any, List, Tuple
from core.schemas import InfrastructureProfile

CITY_NORMALIZATION = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "blr": "Bengaluru",
    "mangaluru": "Mangaluru", "mangalore": "Mangaluru", "ixe": "Mangaluru",
    "hyderabad": "Hyderabad", "hyd": "Hyderabad", "secunderabad": "Hyderabad",
    "goa": "Goa", "madgaon": "Goa", "panaji": "Goa", "baga": "Goa",
    "delhi": "Delhi", "new delhi": "Delhi", "del": "Delhi",
    "mumbai": "Mumbai", "bom": "Mumbai",
    "chennai": "Chennai", "maa": "Chennai",
    "shimla": "Shimla", "simla": "Shimla",
    "dharamshala": "Dharamshala", "dharamsala": "Dharamshala", "mcleodganj": "Dharamshala",
    "chandigarh": "Chandigarh", "kalka": "Kalka", "pathankot": "Pathankot",
    "manali": "Manali", "jaipur": "Jaipur", "kochi": "Kochi", "cochin": "Kochi"
}

# Physical capability matrix: ensures the engine never generates fictional broad-gauge rail or airports
INFRASTRUCTURE_REGISTRY: Dict[str, InfrastructureProfile] = {
    "Bengaluru": InfrastructureProfile(has_airport=True, airport_code="BLR", has_railway_station=True, station_code="SBC"),
    "Mangaluru": InfrastructureProfile(has_airport=True, airport_code="IXE", has_railway_station=True, station_code="MAQ"),
    "Hyderabad": InfrastructureProfile(has_airport=True, airport_code="HYD", has_railway_station=True, station_code="SC"),
    "Goa": InfrastructureProfile(has_airport=True, airport_code="GOI", has_railway_station=True, station_code="MAO"),
    "Delhi": InfrastructureProfile(has_airport=True, airport_code="DEL", has_railway_station=True, station_code="NDLS"),
    "Mumbai": InfrastructureProfile(has_airport=True, airport_code="BOM", has_railway_station=True, station_code="CSMT"),
    "Chennai": InfrastructureProfile(has_airport=True, airport_code="MAA", has_railway_station=True, station_code="MAS"),
    "Chandigarh": InfrastructureProfile(has_airport=True, airport_code="IXC", has_railway_station=True, station_code="CDG"),
    "Pathankot": InfrastructureProfile(has_airport=False, has_railway_station=True, station_code="PTKC"),
    "Kalka": InfrastructureProfile(has_airport=False, has_railway_station=True, station_code="KLK"),
    "Jaipur": InfrastructureProfile(has_airport=True, airport_code="JAI", has_railway_station=True, station_code="JP"),
    "Kochi": InfrastructureProfile(has_airport=True, airport_code="COK", has_railway_station=True, station_code="ERS"),
    
    # Mountain/Tier-2 destinations (Broad-gauge rail is physically impossible here)
    "Dharamshala": InfrastructureProfile(
        has_airport=False,  # Regional Gaggal has very limited flights; gateways preferred
        has_railway_station=False, # STRICT: Broad-gauge rail DOES NOT exist in Dharamshala
        gateways=["Chandigarh", "Pathankot", "Delhi"]
    ),
    "Shimla": InfrastructureProfile(
        has_airport=False,
        has_railway_station=False, # Broad-gauge ends at Kalka
        gateways=["Chandigarh", "Kalka"]
    ),
    "Manali": InfrastructureProfile(
        has_airport=False,
        has_railway_station=False,
        gateways=["Chandigarh"]
    )
}

CITY_COORDINATES = {
    "Bengaluru": (12.9716, 77.5946),
    "Mangaluru": (12.9141, 74.8560),
    "Hyderabad": (17.3850, 78.4867),
    "Goa": (15.2993, 74.1240),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Chandigarh": (30.7333, 76.7794),
    "Pathankot": (32.2689, 75.6497),
    "Kalka": (30.8333, 76.9333),
    "Dharamshala": (32.2190, 76.3234),
    "Shimla": (31.1048, 77.1734),
    "Manali": (32.2432, 77.1892),
    "Jaipur": (26.9124, 75.7873),
    "Kochi": (9.9312, 76.2673)
}

def normalize_city_name(name: str) -> str:
    if not name:
        return ""
    clean = name.strip().lower()
    return CITY_NORMALIZATION.get(clean, name.strip().title())

normalize_city = normalize_city_name

def get_infrastructure(city: str) -> InfrastructureProfile:
    norm = normalize_city_name(city)
    return INFRASTRUCTURE_REGISTRY.get(norm, InfrastructureProfile(has_airport=True, has_railway_station=True))

def get_coordinates(city: str) -> Tuple[float, float]:
    norm = normalize_city_name(city)
    return CITY_COORDINATES.get(norm, (20.5937, 78.9629))

def haversine_km(coord1, coord2) -> float:
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)