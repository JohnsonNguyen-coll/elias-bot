import httpx
import asyncio
import json

async def test_chain(chain: str):
    url = f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools"
    params = {"include": "base_token", "page": 1}
    headers = {"Accept": "application/json;version=20230302"}
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params, headers=headers, timeout=10)
        print(f"\n{'='*40}")
        print(f"Chain: {chain} → HTTP {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            pools = data.get("data", [])
            print(f"Số pools trả về: {len(pools)}")
            if pools:
                # In thông tin pool đầu tiên
                first = pools[0]
                attrs = first.get("attributes", {})
                print(f"Pool đầu tiên: {attrs.get('name', 'N/A')}")
                print(f"  price_usd: {attrs.get('base_token_price_usd')}")
                print(f"  market_cap_usd: {attrs.get('market_cap_usd')}")
                print(f"  fdv_usd: {attrs.get('fdv_usd')}")
                print(f"  volume_h24: {attrs.get('volume_usd', {}).get('h24')}")
        else:
            print(f"Lỗi: {res.text[:200]}")

async def test_networks():
    """Kiểm tra xem monad có trong danh sách networks không"""
    url = "https://api.geckoterminal.com/api/v2/networks"
    params = {"page": 1}
    headers = {"Accept": "application/json;version=20230302"}
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params, headers=headers, timeout=10)
        data = res.json()
        networks = data.get("data", [])
        
        print(f"\n{'='*40}")
        print(f"Tìm 'monad' trong {len(networks)} networks...")
        
        for n in networks:
            nid = n.get("id", "")
            name = n.get("attributes", {}).get("name", "")
            if "monad" in nid.lower() or "monad" in name.lower():
                print(f"  ✅ Tìm thấy: id={nid}, name={name}")

async def main():
    print("Testing GeckoTerminal API...")
    
    # Test từng chain
    for chain in ["eth", "base", "monad"]:
        await test_chain(chain)
    
    # Tìm monad trong networks
    await test_networks()

asyncio.run(main())