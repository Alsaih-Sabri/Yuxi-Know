"""
Script to translate agent names and descriptions from Chinese to English
Run this script to update all agent data in the database
"""

import sqlite3
from pathlib import Path

# Agent translations
AGENT_TRANSLATIONS = {
    "智能聊天助手": {
        "name": "Smart Chat Assistant",
        "description": "Basic AI conversation assistant with tool calling, MCP support, and rich knowledge base capabilities."
    },
    "深度分析智能体": {
        "name": "Deep Analysis Agent",
        "description": "An intelligent agent with planning, deep analysis, and sub-agent collaboration capabilities, capable of handling complex multi-step tasks."
    },
    "智能体 Demo": {
        "name": "Agent Demo",
        "description": "An example agent based on built-in tools."
    },
    "数据库报表助手": {
        "name": "Database Report Assistant",
        "description": "An intelligent assistant that can generate SQL query reports and create charts using the Charts MCP."
    }
}

def translate_agents():
    """Update agent names and descriptions in the database"""
    
    # Database path
    db_path = Path(__file__).parent.parent / "saves" / "database" / "server.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    print(f"📂 Connecting to database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if agents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
        if not cursor.fetchone():
            print("❌ 'agents' table not found in database")
            conn.close()
            return
        
        # Get current agents
        cursor.execute("SELECT id, name, description FROM agents")
        agents = cursor.fetchall()
        
        if not agents:
            print("⚠️  No agents found in database")
            conn.close()
            return
        
        print(f"\n📋 Found {len(agents)} agents in database:")
        for agent_id, name, desc in agents:
            print(f"  - ID: {agent_id}, Name: {name}")
        
        # Update agents
        updated_count = 0
        for chinese_name, translation in AGENT_TRANSLATIONS.items():
            cursor.execute(
                "UPDATE agents SET name = ?, description = ? WHERE name = ?",
                (translation["name"], translation["description"], chinese_name)
            )
            
            if cursor.rowcount > 0:
                print(f"\n✅ Updated: {chinese_name} → {translation['name']}")
                updated_count += 1
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"\n🎉 Successfully updated {updated_count} agents!")
        print("💡 Refresh your browser to see the changes")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting agent translation...\n")
    translate_agents()
