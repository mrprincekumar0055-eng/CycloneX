"""
Multi-Stakeholder Alert Templates for CycloneX
Differentiates actionable guidance for:
1. Citizens
2. Authorities / District Disaster Management
3. Emergency Responders
"""
from typing import Dict, Any, List

ALERT_ACTION_TEMPLATES = {
    "Citizens": {
        "Extreme Risk": [
            "Evacuate immediately to designated multi-purpose cyclone shelters if residing in kutch/thatched houses or within 5km of coastline.",
            "Switch off main domestic gas and electrical supplies before vacating.",
            "Carry waterproof emergency kit: Aadhaar/ID, drinking water (3L/person), dry rations, essential medications, charged power bank.",
            "Keep livestock untied to prevent drowning; move cattle to elevated community enclosures.",
            "Call National Emergency Helpline 112 or State Disaster Control Room for evacuation assistance."
        ],
        "High Risk": [
            "Prepare for impending gale winds and tidal inundation; secure loose rooftop objects and tin sheets.",
            "Stock clean drinking water and non-perishable food for at least 72 hours.",
            "Identify your nearest cyclone shelter and familiarize family members with the evacuation route.",
            "Do not venture near beaches, sea dikes, or flooded riverbeds under any circumstances."
        ],
        "Moderate Risk": [
            "Fishermen in deep sea must return to harbor immediately.",
            "Keep emergency radios, flashlights, and mobile phones fully charged.",
            "Follow verified bulletins from IMD / CycloneX; ignore unverified social media rumors."
        ]
    },
    "Authorities": {
        "Extreme Risk": [
            "Issue mandatory evacuation orders for coastal zones within 0-5 km of projected landfall.",
            "Requisition school buildings, community centers, and pre-identified shelters; verify generator fuel stocks.",
            "Deploy National Disaster Response Force (NDRF) and State Disaster Response Force (SDRF) battalions to forward bases.",
            "Hoisting Port Warning Signal Great Danger Signal No. 8/9/10 at regional sea ports.",
            "Pre-position heavy earthmovers and tree-clearing chainsaws along National and State Highways."
        ],
        "High Risk": [
            "Activate District Emergency Operation Centers (DEOCs) on 24x7 high alert.",
            "Suspend fishing trawler operations and close coastal tourism activities.",
            "Review district hospital generator backups, oxygen supplies, and anti-snake venom availability.",
            "Direct civil supplies department to pre-position dry food packets and water tankers at block headquarters."
        ],
        "Moderate Risk": [
            "Issue advisory to local fishermen to refrain from venturing into open sea.",
            "Inspect drainage sluice gates and coastal embankments for structural integrity."
        ]
    },
    "Emergency Responders": {
        "Extreme Risk": [
            "Stage inflatable motorized rescue boats (IRBs) and life jackets at designated staging hubs outside flood swaths.",
            "Test satellite communication phones (Inmarsat/Iridium) and VHF radio relays.",
            "Set up forward medical triage posts equipped for trauma and hypothermia management.",
            "Prepare mobile water purification units for immediate deployment post-landfall."
        ],
        "High Risk": [
            "Ensure emergency rescue vehicles are fueled and fitted with high-clearance snorkels.",
            "Brief rescue teams on regional topography, low-lying culverts, and vulnerable hamlets.",
            "Coordinate with Indian Coast Guard for continuous aerial/maritime search-and-rescue readiness."
        ],
        "Moderate Risk": [
            "Maintain standby teams at regional battalion headquarters."
        ]
    }
}

