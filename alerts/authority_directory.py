"""
CycloneX Authority & Stakeholder Directory
Maps affected coastal/inland Indian districts to concerned disaster management
authorities, emergency response battalions, maritime authorities, and citizen channels.
"""
from typing import Dict, List, Any

# Primary coastal districts and their respective state & emergency administrative contacts
DISTRICT_AUTHORITY_DIRECTORY: Dict[str, Dict[str, Any]] = {
    # Gujarat Coastline
    "Kutch": {
        "state": "Gujarat",
        "ddma_collector": "District Collector & DM, Kutch (Bhuj)",
        "ddma_email": "collector-kutch@gujarat.gov.in",
        "ddma_phone": "+91-2832-250020",
        "sdma": "Gujarat State Disaster Management Authority (GSDMA)",
        "sdma_email": "controlroom@gsdma.org",
        "ndrf_battalion": "6th Battalion NDRF (Jarod / Gandhinagar)",
        "ndrf_contact": "+91-79-2324-0000",
        "coast_guard": "ICG Station Vadinar / Jakhau Port",
        "ports": ["Kandla (Deendayal Port)", "Mundra Port", "Jakhau Fishery Port"]
    },
    "Devbhumi Dwarka": {
        "state": "Gujarat",
        "ddma_collector": "District Collector, Devbhumi Dwarka (Khambhalia)",
        "ddma_email": "collector-dwarka@gujarat.gov.in",
        "ddma_phone": "+91-2833-232120",
        "sdma": "Gujarat State Disaster Management Authority (GSDMA)",
        "sdma_email": "controlroom@gsdma.org",
        "ndrf_battalion": "6th Battalion NDRF",
        "ndrf_contact": "+91-79-2324-0000",
        "coast_guard": "ICG Station Okha",
        "ports": ["Okha Port", "Salaya Port"]
    },
    "Jamnagar": {
        "state": "Gujarat",
        "ddma_collector": "District Collector & DM, Jamnagar",
        "ddma_email": "collector-jam@gujarat.gov.in",
        "ddma_phone": "+91-288-2550100",
        "sdma": "GSDMA Gandhinagar",
        "sdma_email": "controlroom@gsdma.org",
        "ndrf_battalion": "6th Battalion NDRF",
        "ndrf_contact": "+91-79-2324-0000",
        "coast_guard": "ICG District HQ 1 (Porbandar)",
        "ports": ["Bedi Port", "Sikka Port"]
    },
    "Porbandar": {
        "state": "Gujarat",
        "ddma_collector": "District Collector, Porbandar",
        "ddma_email": "collector-por@gujarat.gov.in",
        "ddma_phone": "+91-286-2246220",
        "sdma": "GSDMA Gandhinagar",
        "sdma_email": "controlroom@gsdma.org",
        "ndrf_battalion": "6th Battalion NDRF",
        "ndrf_contact": "+91-79-2324-0000",
        "coast_guard": "ICG Air Enclave / District HQ Porbandar",
        "ports": ["Porbandar All-Weather Port"]
    },
    "Morbi": {
        "state": "Gujarat",
        "ddma_collector": "District Collector, Morbi",
        "ddma_email": "collector-mor@gujarat.gov.in",
        "ddma_phone": "+91-2822-240100",
        "sdma": "GSDMA Gandhinagar",
        "sdma_email": "controlroom@gsdma.org",
        "ndrf_battalion": "6th Battalion NDRF",
        "ndrf_contact": "+91-79-2324-0000",
        "coast_guard": "ICG Station Vadinar",
        "ports": ["Navlakhi Port"]
    },
    # Odisha Coastline
    "Puri": {
        "state": "Odisha",
        "ddma_collector": "District Collector & DM, Puri",
        "ddma_email": "collector-puri@nic.in",
        "ddma_phone": "+91-6752-222034",
        "sdma": "Odisha State Disaster Management Authority (OSDMA)",
        "sdma_email": "osdma@osdma.org",
        "ndrf_battalion": "3rd Battalion NDRF (Mundali, Cuttack)",
        "ndrf_contact": "+91-671-287-9711",
        "coast_guard": "ICG Station Paradip",
        "ports": ["Astaranga Port"]
    },
    "Jagatsinghpur": {
        "state": "Odisha",
        "ddma_collector": "District Collector, Jagatsinghpur",
        "ddma_email": "collector-jgt@nic.in",
        "ddma_phone": "+91-6724-220379",
        "sdma": "OSDMA Bhubaneswar",
        "sdma_email": "osdma@osdma.org",
        "ndrf_battalion": "3rd Battalion NDRF",
        "ndrf_contact": "+91-671-287-9711",
        "coast_guard": "ICG Station Paradip",
        "ports": ["Paradip Major Port"]
    },
    # Andhra Pradesh Coastline
    "Visakhapatnam": {
        "state": "Andhra Pradesh",
        "ddma_collector": "District Collector, Visakhapatnam",
        "ddma_email": "collector-vsp@ap.gov.in",
        "ddma_phone": "+91-891-256-4848",
        "sdma": "Andhra Pradesh SDMA (APSDMA)",
        "sdma_email": "apsdma@ap.gov.in",
        "ndrf_battalion": "10th Battalion NDRF (Guntur)",
        "ndrf_contact": "+91-863-229-3100",
        "coast_guard": "ICG District HQ 6 (Visakhapatnam)",
        "ports": ["Visakhapatnam Major Port", "Gangavaram Port"]
    },
    # West Bengal Coastline
    "South 24 Parganas": {
        "state": "West Bengal",
        "ddma_collector": "District Magistrate, South 24 Parganas (Alipore)",
        "ddma_email": "dm-s24pgs@wb.gov.in",
        "ddma_phone": "+91-33-2479-1385",
        "sdma": "West Bengal Disaster Management & Civil Defence",
        "sdma_email": "wbdmd@wb.gov.in",
        "ndrf_battalion": "2nd Battalion NDRF (Haringhata / Kolkata)",
        "ndrf_contact": "+91-33-2589-0000",
        "coast_guard": "ICG Regional HQ (North East) Kolkata / Haldia",
        "ports": ["Kolkata Port Trust / Diamond Harbour"]
    },
    # Tamil Nadu Coastline
    "Nagapattinam": {
        "state": "Tamil Nadu",
        "ddma_collector": "District Collector, Nagapattinam",
        "ddma_email": "collrngp@nic.in",
        "ddma_phone": "+91-4365-252700",
        "sdma": "Tamil Nadu State Disaster Management Authority (TNSDMA)",
        "sdma_email": "tnsdma@tn.gov.in",
        "ndrf_battalion": "4th Battalion NDRF (Arakkonam)",
        "ndrf_contact": "+91-4177-226-000",
        "coast_guard": "ICG Station Karaikal",
        "ports": ["Nagapattinam Port"]
    }
}

class AuthorityDirectory:
    @classmethod
    def get_recipients_for_districts(cls, districts: List[str]) -> List[Dict[str, Any]]:
        """
        Gathers contact channels for all authorities and community stakeholders
        across the affected districts.
        """
        recipients = []
        seen_contacts = set()

        for dist in districts:
            info = DISTRICT_AUTHORITY_DIRECTORY.get(dist)
            if not info:
                # Default generic regional authority
                info = {
                    "state": "Coastal Sector",
                    "ddma_collector": f"District Magistrate / Collector ({dist})",
                    "ddma_email": f"controlroom-{dist.lower().replace(' ', '')}@nic.in",
                    "ddma_phone": "+91-1077-EMERGENCY",
                    "sdma": "State Disaster Management Authority (SDMA)",
                    "sdma_email": "sdma-emergency@nic.in",
                    "ndrf_battalion": "NDRF Regional Response Centre",
                    "ndrf_contact": "+91-11-2436-3260",
                    "coast_guard": "Indian Coast Guard District Operations",
                    "ports": ["Coastal Fishery Harbours"]
                }

            # 1. DDMA (District Collector / Emergency Operations Center)
            k_ddma = (info["ddma_email"], "Authorities")
            if k_ddma not in seen_contacts:
                seen_contacts.add(k_ddma)
                recipients.append({
                    "name": info["ddma_collector"],
                    "audience": "Authorities",
                    "district": dist,
                    "state": info["state"],
                    "email": info["ddma_email"],
                    "phone": info["ddma_phone"],
                    "channels": ["dashboard", "email", "sms"]
                })

            # 2. SDMA State Control Room
            k_sdma = (info["sdma_email"], "Authorities")
            if k_sdma not in seen_contacts:
                seen_contacts.add(k_sdma)
                recipients.append({
                    "name": info["sdma"],
                    "audience": "Authorities",
                    "district": dist,
                    "state": info["state"],
                    "email": info["sdma_email"],
                    "phone": "+91-1070-SDMA",
                    "channels": ["dashboard", "email"]
                })

            # 3. NDRF Battalion / Emergency Responders
            k_ndrf = (info["ndrf_battalion"], "Emergency Responders")
            if k_ndrf not in seen_contacts:
                seen_contacts.add(k_ndrf)
                recipients.append({
                    "name": f"{info['ndrf_battalion']} Control Centre",
                    "audience": "Emergency Responders",
                    "district": dist,
                    "state": info["state"],
                    "email": "ndrf-ops@nic.in",
                    "phone": info["ndrf_contact"],
                    "channels": ["dashboard", "sms"]
                })

            # 4. Coast Guard / Port Officer
            k_cg = (info["coast_guard"], "Emergency Responders")
            if k_cg not in seen_contacts:
                seen_contacts.add(k_cg)
                recipients.append({
                    "name": f"{info['coast_guard']} Maritime Operations",
                    "audience": "Emergency Responders",
                    "district": dist,
                    "state": info["state"],
                    "email": "icg-mrcc@gov.in",
                    "phone": "+91-1554-ICG",
                    "channels": ["dashboard", "email", "sms"]
                })

            # 5. Public Broadcast / Citizens Cell
            k_cit = (f"Civil Alert Channel ({dist})", "Citizens")
            if k_cit not in seen_contacts:
                seen_contacts.add(k_cit)
                recipients.append({
                    "name": f"District Public Broadcast Cell ({dist})",
                    "audience": "Citizens",
                    "district": dist,
                    "state": info["state"],
                    "email": f"citizens-broadcast-{dist.lower()}@nic.in",
                    "phone": "+91-CAP-BROADCAST",
                    "channels": ["dashboard", "sms"]
                })

        return recipients

