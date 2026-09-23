from typing import List
from core.schemas import GenericJourneyPlan, TravelMission

class JourneyOptimizer:

    @staticmethod
    def score_plans(plans: List[GenericJourneyPlan], mission: TravelMission) -> List[GenericJourneyPlan]:
        if not plans:
            return []

        costs = [p.total_cost for p in plans]
        min_cost, max_cost = min(costs), max(costs)
        cost_range = max(1.0, max_cost - min_cost)

        for p in plans:
            norm_cost = 1.0 - ((p.total_cost - min_cost) / cost_range)
            norm_buffer = min(1.0, (p.buffer_minutes or 60) / 120.0)
            transfer_penalty = max(0.0, p.transfers_count * 0.10)

            # Check preference bonus
            categories = [leg.category for leg in p.legs]
            pref_bonus = 0.25 if mission.transport_preference in categories else 0.0

            mode = mission.optimization_mode
            if mode == "cheapest":
                score = (norm_cost * 0.75) + (norm_buffer * 0.15) + pref_bonus - transfer_penalty
            elif mode == "fastest":
                score = (norm_cost * 0.20) + (norm_buffer * 0.70) + pref_bonus - transfer_penalty
            else:  # balanced
                score = (norm_cost * 0.45) + (norm_buffer * 0.35) + pref_bonus - transfer_penalty

            p.score = round(max(0.01, score), 3)

        return sorted(plans, key=lambda x: x.score, reverse=True)