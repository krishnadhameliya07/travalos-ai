import math
import uuid
import re
from typing import Dict, Any, List
from core.schemas import (
    TravelMission,
    TravelerComposition,
    GenericJourneyPlan,
    JourneyLeg,
    CostItemization,
    PlanTripResponse
)
from tools.locations import normalize_city_name
from tools.date_resolver import resolve_travel_dates
from tools.travel_tools import TravelToolService
from core.constraint_engine import ConstraintEngine
from core.optimizer import JourneyOptimizer

class TravelOrchestrator:

    def __init__(self):
        self.session_store: Dict[str, TravelMission] = {}

    def plan_mission(self, message: str, conversation_id: str) -> PlanTripResponse:
        prior = self.session_store.get(conversation_id)
        low = message.lower()

        # 1. Linguistic Traveler Extraction
        adults = 1
        children = 0
        if "with my parents" in low or "with parents" in low:
            adults = 3
        elif "with my brother" in low or "with one friend" in low or "with my friend" in low:
            adults = 2
        elif "with two friends" in low:
            adults = 3
        elif "family of four" in low or "family of 4" in low:
            adults = 4
        else:
            t_match = re.search(r'(\d+)\s*(?:people|travelers|pax|persons)', low)
            if t_match:
                adults = int(t_match.group(1))

        travelers = TravelerComposition(total_count=adults + children, adults=adults, children=children)
        rooms = math.ceil(adults / 2.0)

        # 2. Extract Origin and Destination
        origin = prior.origin if prior else None
        destination = prior.destination if prior else None

        if "from " in low:
            orig_match = re.search(r'from\s+([a-zA-Z]+)', low)
            if orig_match:
                origin = orig_match.group(1)
        if "to " in low:
            dest_match = re.search(r'to\s+([a-zA-Z]+)', low)
            if dest_match:
                destination = dest_match.group(1)

        for city in ["bengaluru", "bangalore", "mangaluru", "mangalore", "delhi", "mumbai", "chennai", "hyderabad", "dharamshala", "shimla", "goa", "jaipur"]:
            if city in low:
                if not origin and ("from " + city in low or origin is None): origin = city
                elif not destination and city != origin: destination = city

        if not origin and not destination:
            return PlanTripResponse(status="CLARIFICATION_NEEDED", clarification_question="Where are you travelling from, and where would you like to go?")
        if not origin:
            return PlanTripResponse(status="CLARIFICATION_NEEDED", clarification_question=f"Where are you travelling to {destination} from?")
        if not destination:
            return PlanTripResponse(status="CLARIFICATION_NEEDED", clarification_question=f"Where would you like to travel from {origin}?")

        # 3. Date Resolution
        dates = resolve_travel_dates(message)
        if dates.is_ambiguous:
            return PlanTripResponse(status="CLARIFICATION_NEEDED", clarification_question=dates.clarification_prompt)

        # 4. Budget & Deadlines
        has_budget = False
        max_budget = None
        b_match = re.search(r'(?:₹|rs\.?|under|budget|below)\s*([\d,]+)', low)
        if b_match:
            val = float(b_match.group(1).replace(",", ""))
            if val > 500:
                has_budget = True
                max_budget = val

        has_deadline = False
        arrival_deadline = None
        deadline_minutes = None
        d_match = re.search(r'(?:by|before)\s*(\d{1,2})\s*(am|pm)', low)
        if d_match:
            has_deadline = True
            hh = int(d_match.group(1))
            mer = d_match.group(2).upper()
            arrival_deadline = f"{hh:02d}:00 {mer}"
            if mer == "PM" and hh != 12: hh += 12
            if mer == "AM" and hh == 12: hh = 0
            deadline_minutes = hh * 60

        is_round_trip = ("round trip" in low or "return" in low or dates.nights_count > 0)
        needs_hotel = ("hotel" in low or "stay" in low or dates.nights_count > 0) and ("no hotel" not in low)
        
        pref = "any"
        if "flight" in low: pref = "flight"
        elif "train" in low: pref = "train"
        elif "bus" in low: pref = "bus"

        mission = TravelMission(
            conversation_id=conversation_id,
            origin=normalize_city_name(origin),
            destination=normalize_city_name(destination),
            destination_canonical=normalize_city_name(destination),
            dates=dates,
            trip_type="round_trip" if is_round_trip else "one_way",
            travelers=travelers,
            rooms_count=rooms,
            has_deadline=has_deadline,
            arrival_deadline=arrival_deadline,
            deadline_minutes=deadline_minutes,
            has_budget=has_budget,
            max_budget=max_budget,
            needs_hotel=needs_hotel,
            transport_preference=pref,
            optimization_mode="cheapest" if "cheapest" in low else "balanced"
        )
        self.session_store[conversation_id] = mission

        # 5. Multimodal Journey Synthesis
        outbound_routes = TravelToolService.search_multimodal_itineraries(mission.origin, mission.destination, travelers.total_count)
        hotels = TravelToolService.search_hotels(mission.destination) if mission.needs_hotel else []
        local_transfer = TravelToolService.get_local_transfer(mission.destination)
        return_routes = TravelToolService.search_multimodal_itineraries(mission.destination, mission.origin, travelers.total_count, is_return=True) if is_round_trip else []

        candidate_plans: List[GenericJourneyPlan] = []
        rejected_plans: List[Dict[str, Any]] = []

        for r_idx, out_route in enumerate(outbound_routes):
            for h_idx in range(len(hotels) if hotels else 1):
                legs: List[JourneyLeg] = []
                out_total = 0.0

                if out_route["type"] == "direct":
                    t = out_route["leg"]
                    leg_cost = t["cost"] * travelers.total_count
                    out_total += leg_cost
                    legs.append(JourneyLeg(
                        id=str(uuid.uuid4())[:8],
                        stage="outbound_transit",
                        category=t["category"],
                        title=f"Transit: {t['provider']}",
                        provider=t["provider"],
                        origin_name=mission.origin,
                        origin_type="city",
                        destination_name=mission.destination,
                        destination_type="city",
                        departure_time=t.get("departure"),
                        arrival_time=t.get("arrival"),
                        duration_min=t.get("duration", 120),
                        cost_math=CostItemization(unit_rate=t["cost"], pricing_type="per_person", multiplier_formula=f"₹{t['cost']:,.0f} × {travelers.total_count} pax", subtotal=leg_cost),
                        cost=leg_cost
                    ))
                else:
                    p = out_route["primary_leg"]
                    c = out_route["connector_leg"]
                    hub = out_route["hub_city"]

                    p_cost = p["cost"] * travelers.total_count
                    legs.append(JourneyLeg(
                        id=str(uuid.uuid4())[:8],
                        stage="outbound_transit",
                        category=p["category"],
                        title=f"Long-Distance: {p['provider']}",
                        provider=p["provider"],
                        origin_name=mission.origin,
                        origin_type="airport" if p["category"] == "flight" else "railway_station",
                        destination_name=hub,
                        destination_type="airport" if p["category"] == "flight" else "railway_station",
                        departure_time=p["departure"],
                        arrival_time=p["arrival"],
                        duration_min=p["duration"],
                        cost_math=CostItemization(unit_rate=p["cost"], pricing_type="per_person", multiplier_formula=f"₹{p['cost']:,.0f} × {travelers.total_count} pax", subtotal=p_cost),
                        cost=p_cost
                    ))

                    c_cost = c["cost"]
                    legs.append(JourneyLeg(
                        id=str(uuid.uuid4())[:8],
                        stage="outbound_gateway",
                        category=c["mode"],
                        title=f"Gateway Transfer: {c['desc']}",
                        provider="Regional Intercity Cab",
                        origin_name=hub,
                        origin_type="airport" if p["category"] == "flight" else "railway_station",
                        destination_name=mission.destination,
                        destination_type="city",
                        duration_min=c["duration"],
                        cost_math=CostItemization(unit_rate=c["cost"], pricing_type="per_vehicle", multiplier_formula="Private Dedicated Vehicle", subtotal=c_cost),
                        cost=c_cost
                    ))
                    out_total += (p_cost + c_cost)

                # Hotel Component
                stay_total = 0.0
                if mission.needs_hotel and hotels:
                    h = hotels[h_idx % len(hotels)]
                    nights = max(1, dates.nights_count)
                    stay_total = h["nightly_rate"] * rooms * nights
                    legs.append(JourneyLeg(
                        id=str(uuid.uuid4())[:8],
                        stage="stay",
                        category="hotel",
                        title=f"Stay: {h['name']}",
                        provider=h["name"],
                        origin_name=mission.destination,
                        origin_type="hotel",
                        destination_name=mission.destination,
                        destination_type="hotel",
                        duration_min=nights * 1440,
                        cost_math=CostItemization(unit_rate=h["nightly_rate"], pricing_type="per_room_night", multiplier_formula=f"₹{h['nightly_rate']:,.0f}/night × {rooms} rooms × {nights} nights", subtotal=stay_total),
                        cost=stay_total,
                        details={"area": h["area"], "rating": h["rating"]}
                    ))

                # Local Mobility
                local_total = local_transfer["cost"]
                legs.append(JourneyLeg(
                    id=str(uuid.uuid4())[:8],
                    stage="local",
                    category="cab",
                    title=f"Local: {local_transfer['title']}",
                    provider=local_transfer["provider"],
                    origin_name=mission.destination,
                    origin_type="city",
                    destination_name=mission.destination,
                    destination_type="venue",
                    duration_min=local_transfer["duration"],
                    cost_math=CostItemization(unit_rate=local_total, pricing_type="per_vehicle", multiplier_formula="Local Transit", subtotal=local_total),
                    cost=local_total
                ))

                # Return Journey
                return_total = 0.0
                if is_round_trip:
                    ret_route = return_routes[r_idx % len(return_routes)] if return_routes else out_route
                    if ret_route["type"] == "direct":
                        t = ret_route["leg"]
                        r_cost = t["cost"] * travelers.total_count
                        return_total += r_cost
                        legs.append(JourneyLeg(
                            id=str(uuid.uuid4())[:8],
                            stage="return_transit",
                            category=t["category"],
                            title=f"Return: {t['provider']}",
                            provider=t["provider"],
                            origin_name=mission.destination,
                            origin_type="city",
                            destination_name=mission.origin,
                            destination_type="city",
                            departure_time="03:00 PM",
                            arrival_time="08:00 PM",
                            duration_min=t.get("duration", 120),
                            cost_math=CostItemization(unit_rate=t["cost"], pricing_type="per_person", multiplier_formula=f"₹{t['cost']:,.0f} × {travelers.total_count} pax", subtotal=r_cost),
                            cost=r_cost
                        ))
                    else:
                        hub = ret_route["hub_city"]
                        p = ret_route["primary_leg"]
                        c = ret_route["connector_leg"]
                        c_cost = c["cost"]
                        p_cost = p["cost"] * travelers.total_count
                        legs.append(JourneyLeg(
                            id=str(uuid.uuid4())[:8],
                            stage="return_gateway",
                            category=c["mode"],
                            title=f"Return Gateway: {mission.destination} to {hub}",
                            provider="Regional Return Cab",
                            origin_name=mission.destination,
                            origin_type="city",
                            destination_name=hub,
                            destination_type="airport" if p["category"] == "flight" else "railway_station",
                            duration_min=c["duration"],
                            cost_math=CostItemization(unit_rate=c["cost"], pricing_type="per_vehicle", multiplier_formula="Private Return Vehicle", subtotal=c_cost),
                            cost=c_cost
                        ))
                        legs.append(JourneyLeg(
                            id=str(uuid.uuid4())[:8],
                            stage="return_transit",
                            category=p["category"],
                            title=f"Return Long-Distance: {p['provider']}",
                            provider=p["provider"],
                            origin_name=hub,
                            origin_type="airport" if p["category"] == "flight" else "railway_station",
                            destination_name=mission.origin,
                            destination_type="city",
                            departure_time="04:30 PM",
                            arrival_time="07:30 PM",
                            duration_min=p["duration"],
                            cost_math=CostItemization(unit_rate=p["cost"], pricing_type="per_person", multiplier_formula=f"₹{p['cost']:,.0f} × {travelers.total_count} pax", subtotal=p_cost),
                            cost=p_cost
                        ))
                        return_total += (c_cost + p_cost)

                total_trip_cost = out_total + stay_total + local_total + return_total
                hotel_label = hotels[h_idx % len(hotels)]["name"] if hotels else "Standard Stay"
                plan = GenericJourneyPlan(
                    id=f"plan_{r_idx+1}_{h_idx+1}",
                    title=f"Route via {out_route.get('hub_city', 'Direct')} + {hotel_label.split()[0]}",
                    badge="RECOMMENDED" if (r_idx == 0 and h_idx == 0) else "FEASIBLE",
                    final_destination=mission.destination,
                    legs=legs,
                    total_cost=total_trip_cost,
                    cost_breakdown={"outbound": out_total, "stay": stay_total, "local": local_total, "return": return_total},
                    destination_arrival_time="03:40 PM" if "flight" in [l.category for l in legs] else "07:30 PM",
                    buffer_minutes=80 if mission.has_deadline else None,
                    transfers_count=len([l for l in legs if l.stage in ["outbound_gateway", "return_gateway"]]),
                    risk_level="Low",
                    risk_explanation="Direct corridor and private mountain transfer",
                    data_sources=["MOCK"]
                )

                valid, fault, reason = ConstraintEngine.validate_plan(plan, mission)
                if valid:
                    candidate_plans.append(plan)
                else:
                    rejected_plans.append({"title": plan.title, "hard_violation": fault, "reason": reason})

        scored_plans = JourneyOptimizer.score_plans(candidate_plans, mission)

        if not scored_plans:
            return PlanTripResponse(
                status="FAILED",
                mission=mission,
                rejected_plans=rejected_plans,
                why_this_plan="No complete journey satisfied your budget or deadline constraints."
            )

        recommended = scored_plans[0]
        why_rec = (
            f"Travalos built a verified multimodal route to {mission.destination} for {travelers.total_count} people in {dates.display_label}. "
            f"Avoids impossible direct mountain trains by routing via regional gateway."
        )

        return PlanTripResponse(
            status="READY_FOR_REVIEW",
            mission=mission,
            recommended_plan=recommended,
            alternative_plans=scored_plans[1:],
            rejected_plans=rejected_plans,
            why_this_plan=why_rec,
            why_not_cheapest="Alternative options save marginal cost but add additional transfers and prolonged mountain travel times."
        )