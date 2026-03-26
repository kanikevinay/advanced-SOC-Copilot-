#!/usr/bin/env python3
"""Quick verification script - Run this to ensure all fixes are applied"""

import sys
from pathlib import Path

def check_text_parser_installed():
    """Verify TextLogParser is installed and registered"""
    try:
        from soc_copilot.data.log_ingestion.parsers.text_log_parser import TextLogParser
        parser = TextLogParser()
        assert '.log' in parser.supported_extensions
        assert '.txt' in parser.supported_extensions
        return True
    except Exception as e:
        print(f"ERROR: TextLogParser not found: {e}")
        return False

def check_parser_factory():
    """Verify parser factory recognizes .log files"""
    try:
        from soc_copilot.data.log_ingestion.parser_factory import ParserFactory
        factory = ParserFactory()
        parser = factory.get_parser('.log')
        assert parser is not None
        assert parser.format_name == 'Text'
        return True
    except Exception as e:
        print(f"ERROR: Parser factory issue: {e}")
        return False

def check_log_parsing():
    """Verify test log file can be parsed"""
    try:
        from soc_copilot.data.log_ingestion import parse_log_file
        log_file = r"c:\Users\kanik\Downloads\soc_test_logs.log"
        records = parse_log_file(log_file)
        assert len(records) == 37, f"Expected 37 records, got {len(records)}"
        return True
    except Exception as e:
        print(f"ERROR: Log parsing failed: {e}")
        return False

def check_ml_models():
    """Verify ML models are available"""
    try:
        import joblib
        from pathlib import Path
        
        models_dir = Path("data/models")
        if_model = models_dir / "isolation_forest_v1.joblib"
        rf_model = models_dir / "random_forest_v1.joblib"
        
        assert if_model.exists(), f"IF model not found: {if_model}"
        assert rf_model.exists(), f"RF model not found: {rf_model}"
        
        # Try loading
        joblib.load(if_model)
        joblib.load(rf_model)
        return True
    except Exception as e:
        print(f"ERROR: ML models issue: {e}")
        return False

if __name__ == "__main__":
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root / "src"))
    
    print("=" * 70)
    print("SOC Copilot - Post-Fix Verification")
    print("=" * 70)
    
    checks = [
        ("Text Log Parser Installed", check_text_parser_installed),
        ("Parser Factory Configured", check_parser_factory),
        ("Log File Can Be Parsed", check_log_parsing),
        ("ML Models Available", check_ml_models),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            status = "✓ PASS" if result else "✗ FAIL"
            results.append((name, result))
            print(f"{status}: {name}")
        except Exception as e:
            results.append((name, False))
            print(f"✗ FAIL: {name}")
            print(f"         {e}")
    
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\nProject is fully fixed and ready to use!")
        print("You can now:")
        print("  1. Run: python launch_ui.py")
        print("  2. Upload your log files via the UI")
        print("  3. Enjoy threat detection and alert generation!")
        sys.exit(0)
    else:
        print(f"⚠️  SOME CHECKS FAILED ({passed}/{total})")
        print("\nPlease review the errors above")
        sys.exit(1)
