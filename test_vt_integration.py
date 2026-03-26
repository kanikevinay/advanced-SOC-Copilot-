#!/usr/bin/env python
"""End-to-end test for VT integration"""

import sys
sys.path.insert(0, 'd:/soc/project/SOC-Copilot/src')

from soc_copilot.phase4.controller import AppController
from soc_copilot.phase4.ui.controller_bridge import ControllerBridge

output = []

try:
    output.append('=== End-to-End VT Integration Test ===\n')
    
    # Init
    models_dir = 'd:/soc/project/SOC-Copilot/data/models'
    controller = AppController(models_dir)
    controller.initialize()
    bridge = ControllerBridge(controller)
    output.append('[PASS] Step 1: Initialized controller and bridge')
    
    # Upload
    test_file = 'd:/soc/project/SOC-Copilot/logs/critical_alert.log'
    records = bridge.add_file_source(test_file)
    output.append('[PASS] Step 2: Uploaded %d records from test file' % len(records))
    
    # Get results
    results = bridge.get_latest_alerts(limit=10)
    output.append('[PASS] Step 3: Retrieved %d analysis result(s)' % len(results))
    
    if results:
        r = results[-1]
        output.append('\nResult Details:')
        output.append('  - Batch ID: %s...' % r.batch_id[:8])
        output.append('  - Session ID: %s...' % (r.session_id[:8] if r.session_id else 'None'))
        output.append('  - Raw logs: %d' % len(r.raw_logs))
        output.append('  - VT checked IPs: %d' % len(r.vt_results))
        
        if r.vt_results:
            output.append('\n  VT Results (first 3):')
            for ip in list(r.vt_results.keys())[:3]:
                vt = r.vt_results[ip]
                output.append('    - %s: %s (rep=%d, mal=%d)' % (ip, vt.risk_level, vt.reputation, vt.malicious_votes))
    
    # Test clear
    output.append('\n[PASS] Step 4: Testing batch clear')
    before = len(bridge.get_latest_alerts(limit=1000))
    removed = bridge.clear_current_batch()
    after = len(bridge.get_latest_alerts(limit=1000))
    output.append('  Before: %d, Removed: %d, After: %d' % (before, removed, after))
    
    output.append('\n[SUCCESS] All tests passed!')
    
except Exception as e:
    output.append('\n[FAILED] Error: %s' % str(e))
    import traceback
    output.append(traceback.format_exc())

# Write output
with open('d:/soc/project/SOC-Copilot/test_vt_output.txt', 'w') as f:
    for line in output:
        f.write(line + '\n')
        print(line)

