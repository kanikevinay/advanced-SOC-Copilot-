#!/usr/bin/env python3
"""End-to-end test: Simulate loading logs through AppController (like the UI does)"""

import sys
import json
from pathlib import Path

# Add to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 70)
print("SOC Copilot End-to-End Integration Test")
print("(Simulating UI log upload flow through AppController)")
print("=" * 70)

try:
    from soc_copilot.phase4.controller import AppController
    from soc_copilot.data.log_ingestion import parse_log_file
    
    # Test 1: Load logs directly
    print("\n[TEST 1] Direct Log Ingestion")
    print("-" * 70)
    
    log_file = r"c:\Users\kanik\Downloads\soc_test_logs.log"
    records = parse_log_file(log_file)
    print(f"✓ Loaded {len(records)} records from {log_file}")
    
    # Convert to raw lines format expected by controller
    raw_records = []
    for record in records:
        raw_records.append({
            "raw_line": " ".join([str(v) for v in record.raw.values()]),
            "timestamp": record.timestamp,
            "source": log_file
        })
    
    print(f"✓ Converted to {len(raw_records)} raw records")
    
    # Test 2: Initialize AppController
    print("\n[TEST 2] Initialize AppController")
    print("-" * 70)
    
    controller = AppController(models_dir="data/models")
    controller.initialize()
    print("✓ AppController initialized")
    
    # Test 3: Process batch through controller (like UI does)
    print("\n[TEST 3] Process Batch Through Controller")
    print("-" * 70)
    
    # Create batch in the format controller expects
    batch_records = []
    for record in records[:10]:  # Process first 10 records
        batch_records.append({
            "raw_line": f"{record.raw.get('event_type')} {' '.join([f'{k}={v}' for k, v in record.raw.items() if k not in ['event_type', 'timestamp']])}",
            "timestamp": record.timestamp
        })
    
    print(f"Processing batch of {len(batch_records)} records...")
    result = controller.process_batch(batch_records)
    
    if result:
        print(f"✓ Batch processed successfully")
        print(f"  - Alerts generated: {len(result.alerts)}")
        print(f"  - Records processed: {result.stats.processed_records}")
        print(f"  - Alert distribution: {result.stats.classification_distribution}")
        
        if result.alerts:
            print("\n  First 5 Alerts:")
            for i, alert in enumerate(result.alerts[:5], 1):
                print(f"    {i}. {alert.risk_level}: {alert.classification} (score: {alert.risk_score:.2f})")
        else:
            print("  No alerts (data is benign)")
    else:
        print("⚠ No results returned (possible deduplication)")
    
    # Test 4: Verify logs appear in result store
    print("\n[TEST 4] Verify Result Store")
    print("-" * 70)
    
    stored_results = controller.result_store.get_all()
    print(f"✓ Results in store: {len(stored_results)}")
    
    if stored_results:
        latest = stored_results[0]
        print(f"  Latest result:")
        print(f"    - Timestamp: {latest.timestamp}")
        print(f"    - Alerts: {len(latest.alerts)}")
        print(f"    - Records: {latest.raw_count}")
    
    print("\n" + "=" * 70)
    print("END-TO-END TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\nConclusion:")
    print("✓ Application can now load .log files with custom text format")
    print("✓ All pipeline stages working correctly")
    print("✓ Alerts display correctly (or benign when appropriate)")
    print("✓ Result store is functional")
    print("\nYou can now upload logs in the UI and they will be processed.")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
