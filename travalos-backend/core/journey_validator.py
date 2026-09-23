from typing import Tuple, Optional
from core.schemas import GenericJourneyPlan, TravelMission
from tools.locations import normalize_city_name, get_infrastructure

class JourneyValidator:

    @staticmethod
    def validate_topology(plan: GenericJourneyPlan, mission: TravelMission) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates:
        1. Destination Fidelity (Journey final destination == Requested destination)
        2. Mode vs Infrastructure (Trains only if destination has a railway station)
        3. Spatial Continuity (Leg[i].destination == Leg[i+1].origin)
        """
        req_dest = normalize_city_name(mission.destination)
        plan_final = normalize_city_name(plan.final_destination)

        # 1. Strict Destination Fidelity
        if plan_final != req_dest:
            return False, "Destination Mismatch", f"Journey terminates at hub '{plan_final}', failing to reach requested '{req_dest}'."

        # 2. Mode vs Location Infrastructure Capability
        for leg in plan.legs:
            dest_infra = get_infrastructure(leg.destination_name)
            if leg.category == "train" and not dest_infra.has_railway_station:
                return False, "Invalid Transport Infrastructure", (
                    f"Physical violation: Direct train assigned to '{leg.destination_name}', "
                    f"which has no railway connection."
                )
            if leg.category == "flight" and not dest_infra.has_airport:
                return False, "Invalid Airport Infrastructure", (
                    f"Physical violation: Flight assigned to '{leg.destination_name}', "
                    f"which has no commercial airport."
                )

        # 3. Spatial Continuity across transit legs
        transit_legs = [l for l in plan.legs if l.category in ["flight", "train", "bus", "cab"]]
        for i in range(len(transit_legs) - 1):
            curr_dest = normalize_city_name(transit_legs[i].destination_name)
            next_orig = normalize_city_name(transit_legs[i+1].origin_name)
            if curr_dest != next_orig and curr_dest != req_dest:
                return False, "Discontinuous Route", f"Route breaks: arrives in '{curr_dest}' but next leg departs from '{next_orig}'."

        return True, None, None