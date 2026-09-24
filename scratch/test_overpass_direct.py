import httpx
import asyncio

async def test():
    query = """
    [out:json][timeout:10];
    (
      node["amenity"="hospital"](22.0, 68.5, 23.5, 70.0);
      node["emergency"="shelter"](22.0, 68.5, 23.5, 70.0);
    );
    out body;
    """
    headers = {
        "User-Agent": "CycloneX-SIH26070-Research/1.0 (contact@cyclonex.gov)"
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        mirrors = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
            "https://overpass-api.de/api/interpreter"
        ]
        for m in mirrors:
            try:
                print(f"Testing mirror: {m}")
                res = await client.post(m, data={"data": query}, headers=headers)
                print(f"  Status: {res.status_code}")
                if res.status_code == 200:
                    data = res.json()
                    elements = data.get("elements", [])
                    print(f"  Elements: {len(elements)}")
                    if elements:
                        for el in elements[:3]:
                            print(f"    - {el.get('tags', {}).get('name', 'Facility')} ({el.get('lat')}, {el.get('lon')})")
                        break
            except Exception as e:
                print(f"  Failed on {m}: {e}")

asyncio.run(test())
