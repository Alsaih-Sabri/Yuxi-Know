#!/usr/bin/env python3
"""Check LightRAG knowledge graph data"""

import sys
sys.path.insert(0, '/app')

from src import knowledge_base
import asyncio

async def check_lightrag():
    # Get the database
    dbs = knowledge_base.get_databases()['databases']
    my_business_db = next((db for db in dbs if db.get('name') == 'my bussiness'), None)
    
    if not my_business_db:
        print("Database 'my_bussiness' not found!")
        return
    
    db_id = my_business_db['db_id']
    print(f"\n{'='*60}")
    print(f"Checking LightRAG data for: {my_business_db['name']}")
    print(f"Database ID: {db_id}")
    print(f"{'='*60}\n")
    
    # Try to query with different keywords
    test_queries = [
        "Sabri",
        "sabri",
        "person",
        "name",
        "identity",
        "who",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        try:
            results = await knowledge_base.aquery(query, db_id)
            if results:
                print(f"   ✅ Found results: {len(results) if isinstance(results, list) else 'text response'}")
                if isinstance(results, str):
                    print(f"   Response preview: {results[:200]}...")
                else:
                    print(f"   First result: {results[0] if results else 'None'}")
            else:
                print(f"   ❌ No results found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(check_lightrag())
