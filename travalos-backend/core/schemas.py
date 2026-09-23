from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

DataSourceType = Literal["LIVE", "MOCK", "ESTIMATED", "CACHE"]
PricingType = Literal["per_person", "per_vehicle", "per_room_night", "flat"]
TripFSMState = Literal[
    "DRAFT", 
    "CLARIFICATION_NEEDED", 
    "PLANNING", 
    "READY_FOR_REVIEW", 
    "CONFIRMED", 
    "FAILED"
]

class InfrastructureProfile(BaseModel):
    has_airport: bool
    airport_code: Optional[str] = None
    has_railway_station: bool
    station_code: Optional[str] = None
    has_bus_terminal: bool = True
    gateways: List[str] = Field(default_factory=list)

class TravelerComposition(BaseModel):
    total_count: int = 1
    adults: int = 1
    children: int = 0
    raw_relationship_text: Optional[str] = None

class ResolvedDates(BaseModel):
    departure_date: str                   # ISO "2026-12-10"
    return_date: Optional[str] = None     # ISO "2026-12-14"
    display_label: str                    # "10–14 Dec 2026 (5 Days, 4 Nights)"
    duration_days: int = 1
    nights_count: int = 0
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None

class CostItemization(BaseModel):
    unit_rate: float
    pricing_type: PricingType
    multiplier_formula: str               # e.g., "₹1,200/night × 2 rooms × 4 nights"
    subtotal: float

class JourneyLeg(BaseModel):
    id: str
    stage: Literal["outbound_transit", "outbound_gateway", "stay", "local", "return_gateway", "return_transit"]
    category: Literal["flight", "train", "bus", "hotel", "cab", "metro", "walk"]
    title: str
    provider: str
    origin_name: str
    origin_type: Literal["city", "airport", "railway_station", "bus_terminal", "hotel", "venue"]
    destination_name: str
    destination_type: Literal["city", "airport", "railway_station", "bus_terminal", "hotel", "venue"]
    departure_time: Optional[str] = None  # "06:10 AM"
    arrival_time: Optional[str] = None    # "08:15 AM"
    duration_min: int
    cost_math: CostItemization
    cost: float
    data_source: DataSourceType = "MOCK"
    details: Dict[str, Any] = Field(default_factory=dict)

class TravelMission(BaseModel):
    conversation_id: str
    origin: str
    destination: str                      # Stated destination (e.g. "Dharamshala")
    destination_canonical: str
    venue_name: Optional[str] = None
    dates: ResolvedDates
    trip_type: Literal["one_way", "round_trip"] = "one_way"
    travelers: TravelerComposition
    rooms_count: int = 1
    has_deadline: bool = False
    arrival_deadline: Optional[str] = None
    deadline_minutes: Optional[int] = None
    has_budget: bool = False
    max_budget: Optional[float] = None
    needs_hotel: bool = True
    hotel_area_preference: Optional[str] = None
    transport_preference: Literal["any", "flight", "train", "bus", "public_preferred"] = "any"
    fallback_transport: Optional[str] = None
    avoid_transfers: bool = False
    optimization_mode: Literal["balanced", "cheapest", "fastest", "convenient"] = "balanced"

class GenericJourneyPlan(BaseModel):
    id: str
    title: str
    badge: str
    final_destination: str                # Must match mission.destination
    legs: List[JourneyLeg]
    total_cost: float
    cost_breakdown: Dict[str, float]      # {"outbound": X, "stay": Y, "local": Z, "return": A}
    destination_arrival_time: Optional[str] = None
    buffer_minutes: Optional[int] = None
    transfers_count: int
    risk_level: Literal["Low", "Medium", "High"]
    risk_explanation: str
    score: float = 0.0
    data_sources: List[DataSourceType] = Field(default_factory=list)

class PlanTripResponse(BaseModel):
    status: TripFSMState
    mission: Optional[TravelMission] = None
    recommended_plan: Optional[GenericJourneyPlan] = None
    alternative_plans: List[GenericJourneyPlan] = Field(default_factory=list)
    rejected_plans: List[Dict[str, Any]] = Field(default_factory=list)
    why_this_plan: str = ""
    why_not_cheapest: str = ""
    clarification_question: Optional[str] = None
    data_source_summary: str = "SIMULATED DATA (Verified Mock Benchmarks)"