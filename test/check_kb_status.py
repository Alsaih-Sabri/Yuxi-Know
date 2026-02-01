#!/usr/bin/env python3
"""Check knowledge base status and file indexing"""

import sys
sys.path.insert(0, '/app')

from src import knowledge_base

# Get all databases
dbs = knowledge_base.get_databases()['databases']

print(f"\n{'='*60}")
print(f"Total Knowledge Bases: {len(dbs)}")
print(f"{'='*60}\n")

for db in dbs:
    print(f"📚 Database: {db.get('name', 'Unknown')}")
    print(f"   ID: {db.get('db_id', 'N/A')}")
    print(f"   Type: {db.get('kb_type', 'N/A')}")
    
    files = db.get('files', {})
    print(f"   Total Files: {len(files)}")
    
    if files:
        print(f"\n   Files Status:")
        file_items = list(files.items())[:10] if isinstance(files, dict) else files[:10]
        for i, item in enumerate(file_items, 1):
            if isinstance(item, tuple):
                file_id, f = item
            else:
                f = item
                file_id = f.get('file_id', 'N/A')
            
            status = f.get('status', 'unknown')
            filename = f.get('filename', 'unknown')
            print(f"   {i}. {filename}")
            print(f"      Status: {status}")
            print(f"      File ID: {file_id}")
        
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more files")
    
    print(f"\n{'-'*60}\n")

# Check if "my_bussiness" database exists and has indexed files
my_business_db = next((db for db in dbs if db.get('name') == 'my_bussiness'), None)
if my_business_db:
    files = my_business_db.get('files', {})
    file_list = list(files.values()) if isinstance(files, dict) else files
    indexed_files = [f for f in file_list if f.get('status') == 'indexed']
    parsed_files = [f for f in file_list if f.get('status') == 'parsed']
    
    print(f"\n🔍 'my_bussiness' Database Analysis:")
    print(f"   Total files: {len(file_list)}")
    print(f"   Indexed files: {len(indexed_files)}")
    print(f"   Parsed (not indexed): {len(parsed_files)}")
    
    if parsed_files:
        print(f"\n   ⚠️  WARNING: {len(parsed_files)} files are parsed but NOT indexed!")
        print(f"   These files won't be searchable until indexed.")
        for f in parsed_files:
            print(f"      - {f.get('filename', 'unknown')}")
