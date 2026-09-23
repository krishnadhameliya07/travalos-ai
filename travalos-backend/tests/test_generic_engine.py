import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.orchestrator import TravelOrchestrator

def test_dharamshala_regression():
    orch = TravelOrchestrator()
    prompt = (
        "I’m travelling from Bengaluru to Dharamshala with my parents for 5 days in December. "
        "We are 3 people. We want to keep the total trip under ₹45,000, prefer flights for the long-distance portion "
        "but want to avoid too many transfers. We need a comfortable hotel, and we would like to reach Dharamshala "
        "before 5 PM on the first day. Include the return journey and show me the most practical complete route."
    )
    res = orch.plan_mission(prompt, "conv_dharamshala_test")
    
    assert res.status == "READY_FOR_REVIEW", f"Expected READY_FOR_REVIEW, got {res.status}. Reason: {res.why_this_plan}"
    assert res.mission.destination == "Dharamshala"
    assert res.mission.travelers.total_count == 3
    assert res.mission.rooms_count == 2
    assert "Dec 2026" in res.mission.dates.display_label
    
    plan = res.recommended_plan
    assert plan.final_destination == "Dharamshala"
    assert plan.total_cost <= 45000.0, f"Plan cost {plan.total_cost} exceeds 45,000 budget"
    
    # 1. Assert zero fictional direct trains to Dharamshala across all transit legs
    for leg in plan.legs:
        if leg.stage in ["outbound_transit", "outbound_gateway"]:
            assert leg.category != "train", f"Direct train into Dharamshala is physically impossible! Found {leg.title}"

    # 2. Assert the connecting leg into Dharamshala is valid road transit (cab/bus)
    gateway_legs = [l for l in plan.legs if l.stage == "outbound_gateway"]
    assert len(gateway_legs) > 0, "Expected a gateway connector leg into Dharamshala"
    assert gateway_legs[0].destination_name == "Dharamshala"
    assert gateway_legs[0].category in ["cab", "bus"], f"Connector must be road transit, got {gateway_legs[0].category}"

def test_shimla_gateway_fidelity():
    orch = TravelOrchestrator()
    prompt = "I want to travel from Bangalore to Shimla next month for 3 days with two friends under ₹40,000."
    res = orch.plan_mission(prompt, "conv_shimla_test")
    
    assert res.status == "READY_FOR_REVIEW"
    assert res.mission.destination == "Shimla"
    assert res.mission.travelers.total_count == 3
    assert res.recommended_plan.final_destination == "Shimla"

def test_one_way_isolation():
    orch = TravelOrchestrator()
    prompt = "I need to travel alone from Hyderabad to Jaipur on 18 October. One-way only. No hotel. Budget ₹8,000."
    res = orch.plan_mission(prompt, "conv_oneway_test")
    
    assert res.status == "READY_FOR_REVIEW"
    assert res.mission.trip_type == "one_way"
    assert res.mission.needs_hotel is False
    assert "return" not in [l.stage for l in res.recommended_plan.legs]

if __name__ == "__main__":
    test_dharamshala_regression()
    test_shimla_gateway_fidelity()
    test_one_way_isolation()
    print("ALL 3 REGRESSION TESTS PASSED DETERMINISTICALLY!")