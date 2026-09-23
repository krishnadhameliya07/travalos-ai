import uuid
from typing import List, Dict, Any
from core.schemas import JourneyLeg, CostItemization
from tools.locations import normalize_city_name, get_infrastructure, haversine_km, get_coordinates

# Benchmark Curated Transit Database (Realistic Fares)
CURATED_TRANSIT = [
    # Bengaluru <-> Chandigarh (Gateway for Dharamshala / Shimla / Manali)
    {"origin": "Bengaluru", "destination": "Chandigarh", "category": "flight", "provider": "IndiGo 6E-6745 (Direct)", "departure": "06:25 AM", "arrival": "09:20 AM", "duration": 175, "cost": 3900.0},
    {"origin": "Chandigarh", "destination": "Bengaluru", "category": "flight", "provider": "IndiGo 6E-6746 (Direct Return)", "departure": "04:30 PM", "arrival": "07:30 PM", "duration": 180, "cost": 3900.0},
    {"origin": "Bengaluru", "destination": "Chandigarh", "category": "train", "provider": "Karnataka Sampark Kranti (12629)", "departure": "01:30 PM", "arrival": "01:45 PM", "duration": 2895, "cost": 1850.0},

    # Bengaluru <-> Delhi
    {"origin": "Bengaluru", "destination": "Delhi", "category": "flight", "provider": "Air India AI-505 Express", "departure": "06:00 AM", "arrival": "08:45 AM", "duration": 165, "cost": 3600.0},
    {"origin": "Delhi", "destination": "Bengaluru", "category": "flight", "provider": "Air India AI-506 Return", "departure": "05:15 PM", "arrival": "08:00 PM", "duration": 165, "cost": 3600.0},
    {"origin": "Bengaluru", "destination": "Delhi", "category": "train", "provider": "Karnataka Express (12627)", "departure": "07:20 PM", "arrival": "09:00 AM", "duration": 2260, "cost": 1750.0},

    # Delhi <-> Pathankot Cantt (Gateway for Dharamshala)
    {"origin": "Delhi", "destination": "Pathankot", "category": "train", "provider": "Vande Bharat Express (22439)", "departure": "06:00 AM", "arrival": "11:45 AM", "duration": 345, "cost": 1250.0},
    {"origin": "Pathankot", "destination": "Delhi", "category": "train", "provider": "Vande Bharat Return (22440)", "departure": "04:30 PM", "arrival": "10:15 PM", "duration": 345, "cost": 1250.0},

    # Delhi <-> Kalka (Gateway for Shimla)
    {"origin": "Delhi", "destination": "Kalka", "category": "train", "provider": "Kalka Shatabdi Express (12005)", "departure": "05:15 PM", "arrival": "09:15 PM", "duration": 240, "cost": 850.0},
    {"origin": "Kalka", "destination": "Delhi", "category": "train", "provider": "Kalka Shatabdi Return (12006)", "departure": "06:15 AM", "arrival": "10:15 AM", "duration": 240, "cost": 850.0},

    # Hyderabad <-> Jaipur
    {"origin": "Hyderabad", "destination": "Jaipur", "category": "flight", "provider": "IndiGo 6E-497 (Non-stop)", "departure": "06:45 AM", "arrival": "08:50 AM", "duration": 125, "cost": 4800.0},
    {"origin": "Jaipur", "destination": "Hyderabad", "category": "flight", "provider": "IndiGo 6E-498 (Return)", "departure": "07:30 PM", "arrival": "09:40 PM", "duration": 130, "cost": 4800.0},

    # Mangaluru <-> Goa
    {"origin": "Mangaluru", "destination": "Goa", "category": "bus", "provider": "Kadamba Volvo AC Express", "departure": "06:30 AM", "arrival": "01:30 PM", "duration": 420, "cost": 950.0},
    {"origin": "Goa", "destination": "Mangaluru", "category": "bus", "provider": "Kadamba Volvo AC (Return)", "departure": "02:30 PM", "arrival": "09:30 PM", "duration": 420, "cost": 950.0},
    {"origin": "Mangaluru", "destination": "Goa", "category": "train", "provider": "Vande Bharat Express (20646)", "departure": "08:30 AM", "arrival": "01:15 PM", "duration": 285, "cost": 1250.0},

    # Mangaluru <-> Hyderabad
    {"origin": "Mangaluru", "destination": "Hyderabad", "category": "flight", "provider": "IndiGo 6E-532 (Direct)", "departure": "06:10 AM", "arrival": "08:05 AM", "duration": 115, "cost": 4900.0},
    {"origin": "Hyderabad", "destination": "Mangaluru", "category": "flight", "provider": "IndiGo 6E-533 (Direct Return)", "departure": "06:40 PM", "arrival": "08:35 PM", "duration": 115, "cost": 4900.0},

    # Bengaluru <-> Chennai
    {"origin": "Bengaluru", "destination": "Chennai", "category": "train", "provider": "Vande Bharat Express (20608)", "departure": "05:45 AM", "arrival": "10:25 AM", "duration": 280, "cost": 1050.0},
    {"origin": "Chennai", "destination": "Bengaluru", "category": "train", "provider": "Vande Bharat Return (20607)", "departure": "05:30 PM", "arrival": "10:00 PM", "duration": 270, "cost": 1050.0},
]

# Gateway Mountain Road Connections (per-vehicle private transfers)
ROAD_GATEWAYS = {
    ("Chandigarh", "Dharamshala"): {"mode": "cab", "desc": "Chandigarh to Dharamshala Private Cab (via NH503)", "duration": 330, "cost": 2800.0},
    ("Dharamshala", "Chandigarh"): {"mode": "cab", "desc": "Dharamshala to Chandigarh Return Cab", "duration": 330, "cost": 2800.0},
    ("Pathankot", "Dharamshala"): {"mode": "cab", "desc": "Pathankot Cantt to Dharamshala Station Taxi", "duration": 135, "cost": 1600.0},
    ("Dharamshala", "Pathankot"): {"mode": "cab", "desc": "Dharamshala to Pathankot Return Taxi", "duration": 135, "cost": 1600.0},
    ("Chandigarh", "Shimla"): {"mode": "cab", "desc": "Chandigarh to Shimla Mall Road Cab", "duration": 190, "cost": 2200.0},
    ("Shimla", "Chandigarh"): {"mode": "cab", "desc": "Shimla to Chandigarh Return Cab", "duration": 190, "cost": 2200.0},
    ("Kalka", "Shimla"): {"mode": "train", "desc": "Kalka-Shimla Toy Train Express", "duration": 310, "cost": 320.0},
    ("Shimla", "Kalka"): {"mode": "train", "desc": "Shimla-Kalka Toy Train Express (Return)", "duration": 310, "cost": 320.0},
}

CURATED_HOTELS = [
    # Dharamshala
    {"name": "Dharamshala Pine Valley Villa & Suites", "city": "Dharamshala", "area": "Kotwali Bazaar / McLeod Ganj", "nightly_rate": 1600.0, "rating": 4.4},
    {"name": "Hyatt Regency Dharamshala Resort", "city": "Dharamshala", "area": "McLeod Ganj", "nightly_rate": 5800.0, "rating": 4.8},
    
    # Shimla
    {"name": "Hotel Combermere (Near Mall Road)", "city": "Shimla", "area": "Mall Road", "nightly_rate": 1800.0, "rating": 4.3},
    {"name": "The Oberoi Cecil", "city": "Shimla", "area": "Mall Road", "nightly_rate": 5800.0, "rating": 4.8},

    # Goa & Hyderabad
    {"name": "Resort Baga Beach Heritage", "city": "Goa", "area": "Baga Beach", "nightly_rate": 2200.0, "rating": 4.2},
    {"name": "Lemon Tree Premier Hitec City", "city": "Hyderabad", "area": "Hitec City", "nightly_rate": 3400.0, "rating": 4.3},
]

class TravelToolService:

    @staticmethod
    def search_multimodal_itineraries(origin: str, destination: str, traveler_count: int, is_return: bool = False) -> List[Dict[str, Any]]:
        norm_orig = normalize_city_name(origin)
        norm_dest = normalize_city_name(destination)
        orig_infra = get_infrastructure(norm_orig)
        dest_infra = get_infrastructure(norm_dest)

        results = []

        # 1. Direct search (Only if direct transit is curated and valid)
        for t in CURATED_TRANSIT:
            if t["origin"] == norm_orig and t["destination"] == norm_dest:
                results.append({"type": "direct", "leg": t})

        if results:
            return results

        # 2. Hub-and-Spoke Gateway Routing
        # Outbound: Gateway is discovered from destination's gateways
        if not is_return and dest_infra.gateways:
            for hub in dest_infra.gateways:
                primary_options = [t for t in CURATED_TRANSIT if t["origin"] == norm_orig and t["destination"] == hub]
                connector = ROAD_GATEWAYS.get((hub, norm_dest))
                if primary_options and connector:
                    for p in primary_options:
                        results.append({
                            "type": "multimodal_hub",
                            "primary_leg": p,
                            "connector_leg": connector,
                            "hub_city": hub
                        })
            if results:
                return results

        # Inbound/Return: Gateway is discovered from origin's gateways
        if is_return and orig_infra.gateways:
            for hub in orig_infra.gateways:
                primary_options = [t for t in CURATED_TRANSIT if t["origin"] == hub and t["destination"] == norm_dest]
                connector = ROAD_GATEWAYS.get((norm_orig, hub))
                if primary_options and connector:
                    for p in primary_options:
                        results.append({
                            "type": "multimodal_hub",
                            "primary_leg": p,
                            "connector_leg": connector,
                            "hub_city": hub
                        })
            if results:
                return results

        # 3. Dynamic Synthetic Fallback respecting physical infrastructure
        dist = haversine_km(get_coordinates(norm_orig), get_coordinates(norm_dest))
        synthetic = []
        if dest_infra.has_airport and orig_infra.has_airport:
            flight_cost = round(2800.0 + (dist * 2.6), -1)
            flight_dur = max(60, int((dist / 520.0) * 60) + 40)
            synthetic.append({
                "type": "direct",
                "leg": {
                    "origin": norm_orig, "destination": norm_dest, "category": "flight",
                    "provider": f"Scheduled Express Air ({norm_orig[:3].upper()}→{norm_dest[:3].upper()})",
                    "departure": "07:00 AM", "arrival": "09:30 AM", "duration": flight_dur, "cost": flight_cost
                }
            })
        if dest_infra.has_railway_station and orig_infra.has_railway_station:
            train_cost = round(350.0 + (dist * 1.1), -1)
            train_dur = max(180, int((dist / 65.0) * 60))
            synthetic.append({
                "type": "direct",
                "leg": {
                    "origin": norm_orig, "destination": norm_dest, "category": "train",
                    "provider": f"Superfast Intercity Rail ({norm_orig[:3].upper()})",
                    "departure": "06:15 AM", "arrival": "02:30 PM", "duration": train_dur, "cost": train_cost
                }
            })
        
        return synthetic

    @staticmethod
    def search_hotels(destination: str, area_pref: str = None) -> List[Dict[str, Any]]:
        norm_dest = normalize_city_name(destination)
        matches = [h for h in CURATED_HOTELS if h["city"] == norm_dest]
        if matches:
            if area_pref:
                filtered = [h for h in matches if area_pref.lower() in h["area"].lower()]
                if filtered:
                    return filtered
            # Return sorted by value so budget options are evaluated first
            return sorted(matches, key=lambda x: x["nightly_rate"])
        return [
            {"name": f"{norm_dest} Central Hotel", "city": norm_dest, "area": "City Center", "nightly_rate": 1800.0, "rating": 4.2},
            {"name": f"{norm_dest} Heritage View Stay", "city": norm_dest, "area": "Scenic Enclave", "nightly_rate": 3400.0, "rating": 4.5}
        ]

    @staticmethod
    def get_local_transfer(city: str) -> Dict[str, Any]:
        norm = normalize_city_name(city)
        if norm == "Dharamshala":
            return {"title": "Town Mobility & Monastery Transfer", "provider": "Local Taxi Union", "cost": 450.0, "duration": 25}
        elif norm == "Shimla":
            return {"title": "Mall Road Shuttle Service", "provider": "Shimla Local Transit", "cost": 250.0, "duration": 15}
        elif norm == "Hyderabad":
            return {"title": "ORR Express Airport Cab", "provider": "Pre-paid Airport Taxi", "cost": 650.0, "duration": 45}
        return {"title": f"{norm} Local Mobility", "provider": "City Cab", "cost": 300.0, "duration": 25}