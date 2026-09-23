from typing import Tuple, Optional
from core.schemas import GenericJourneyPlan, TravelMission
from core.journey_validator import JourneyValidator

class ConstraintEngine:

    @staticmethod
    def validate_plan(plan: GenericJourneyPlan, mission: TravelMission) -> Tuple[bool, Optional[str], Optional[str]]:
        # 1. Topological Journey Validation First
        top_ok, top_fault, top_reason = JourneyValidator.validate_topology(plan, mission)
        if not top_ok:
            return False, top_fault, top_reason

        # 2. Hard Budget Constraint
        if mission.has_budget and mission.max_budget:
            if plan.total_cost > mission.max_budget:
                over = plan.total_cost - mission.max_budget
                return False, f"Exceeds Budget by ₹{over:,.0f}", f"Total cost ₹{plan.total_cost:,.0f} exceeds budget limit of ₹{mission.max_budget:,.0f}"

        # 3. Hard Arrival Deadline Constraint
        if mission.has_deadline and mission.deadline_minutes and plan.destination_arrival_time:
            time_parts = plan.destination_arrival_time.replace(":", " ").split()
            if len(time_parts) >= 2:
                hh, mm = int(time_parts[0]), int(time_parts[1])
                is_pm = "PM" in plan.destination_arrival_time.upper()
                if is_pm and hh != 12: hh += 12
                if not is_pm and hh == 12: hh = 0
                arrival_min = (hh * 60) + mm
                if arrival_min > mission.deadline_minutes:
                    delay = arrival_min - mission.deadline_minutes
                    return False, f"Misses Deadline by {delay}m", f"Arrives at {plan.destination_arrival_time}, missing required {mission.arrival_deadline} cutoff"

        return True, None, None