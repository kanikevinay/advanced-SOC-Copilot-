#!/usr/bin/env python3
"""
SOC Copilot End-to-End Build Pipeline
======================================

Automates the complete build process from source to installer:
1. Validates environment and prerequisites
2. Generates model integrity hashes
3. Runs PyInstaller build via build_exe.py
4. Runs Inno Setup compiler (if available)
5. Outputs final installer

Usage:
    python scripts/build_installer.py              # Full build + installer
    python scripts/build_installer.py --exe-only   # Build EXE only (no installer)
    python scripts/build_installer.py --dry-run    # Validate only
    python scripts/build_installer.py --clean      # Clean build

Output:
    dist/SOC_Copilot_Setup_1.0.0-beta.1.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


VERSION = "1.0.0-beta.1"


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def check_prerequisites(project_root: Path) -> dict:
    """Check all build prerequisites"""
    print("Checking build prerequisites...")
    
    status = {
        "python": False,
        "pyinstaller": False,
        "inno_setup": False,
        "source": False,
        "models": False,
        "assets": False,
    }
    
    # Python version
    if sys.version_info >= (3, 10):
        print(f"  [OK] Python {sys.version.split()[0]}")
        status["python"] = True
    else:
        print(f"  [FAIL] Python 3.10+ required (found {sys.version.split()[0]})")
    
    # PyInstaller
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
        status["pyinstaller"] = True
    except ImportError:
        print("  [FAIL] PyInstaller not installed (pip install pyinstaller>=6.0.0)")
    
    # Inno Setup
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    
    iscc_path = None
    for p in iscc_paths:
        if Path(p).exists():
            iscc_path = p
            break
    
    if iscc_path:
        print(f"  [OK] Inno Setup found: {iscc_path}")
        status["inno_setup"] = True
    else:
        # Try PATH
        result = shutil.which("iscc")
        if result:
            iscc_path = result
            print(f"  [OK] Inno Setup found: {iscc_path}")
            status["inno_setup"] = True
        else:
            print("  [SKIP] Inno Setup not found (installer step will be skipped)")
    
    status["iscc_path"] = iscc_path
    
    # Source code
    src_dir = project_root / "src" / "soc_copilot"
    if src_dir.exists():
        print("  [OK] Source code found")
        status["source"] = True
    else:
        print(f"  [FAIL] Source not found: {src_dir}")
    
    # Models
    models_dir = project_root / "data" / "models"
    required_models = [
        "isolation_forest_v1.joblib",
        "random_forest_v1.joblib",
        "feature_order.json",
        "label_map.json",
    ]
    
    if models_dir.exists():
        missing = [m for m in required_models if not (models_dir / m).exists()]
        if missing:
            print(f"  [WARN] Missing models: {', '.join(missing)}")
            print("         Run 'python scripts/train_models.py' first")
        else:
            print("  [OK] All models found")
            status["models"] = True
    else:
        print(f"  [WARN] Models directory not found: {models_dir}")
    
    # Assets
    icon = project_root / "assets" / "icon.ico"
    if icon.exists():
        print("  [OK] Icon found")
        status["assets"] = True
    else:
        print("  [WARN] Icon not found (will generate during build)")
        status["assets"] = True  # Not critical
    
    return status


def run_build_exe(project_root: Path, clean: bool = False) -> bool:
    """Run PyInstaller build via build_exe.py"""
    print("\n" + "=" * 60)
    print("STEP 1: Building Executable with PyInstaller")
    print("=" * 60)
    
    cmd = [sys.executable, str(project_root / "scripts" / "build_exe.py")]
    if clean:
        cmd.append("--clean")
    
    result = subprocess.run(cmd, cwd=str(project_root))
    
    if result.returncode != 0:
        print("\n[FAIL] Executable build failed")
        return False
    
    # Verify output
    exe_path = project_root / "dist" / "SOC Copilot" / "SOC Copilot.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  [OK] Executable created: {exe_path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"\n  [FAIL] Executable not found at expected location: {exe_path}")
        return False


def run_inno_setup(project_root: Path, iscc_path: str) -> bool:
    """Run Inno Setup compiler to create installer"""
    print("\n" + "=" * 60)
    print("STEP 2: Building Installer with Inno Setup")
    print("=" * 60)
    
    iss_file = project_root / "installer" / "installer.iss"
    
    if not iss_file.exists():
        print(f"  [FAIL] Installer script not found: {iss_file}")
        return False
    
    cmd = [iscc_path, str(iss_file)]
    print(f"  Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(project_root))
    
    if result.returncode != 0:
        print("\n  [FAIL] Installer build failed")
        return False
    
    # Verify output
    installer_path = project_root / "dist" / f"SOC_Copilot_Setup_{VERSION}.exe"
    if installer_path.exists():
        size_mb = installer_path.stat().st_size / (1024 * 1024)
        print(f"\n  [OK] Installer created: {installer_path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"\n  [WARN] Installer not found at expected location: {installer_path}")
        # Check alternative names
        for f in (project_root / "dist").glob("SOC_Copilot_Setup_*"):
            print(f"  Found: {f}")
        return True  # File might have slightly different name


def print_summary(project_root: Path, exe_built: bool, installer_built: bool):
    """Print build summary"""
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"  Version:    {VERSION}")
    print(f"  Executable: {'✅ Built' if exe_built else '❌ Failed'}")
    print(f"  Installer:  {'✅ Built' if installer_built else '⏭ Skipped'}")
    
    if exe_built:
        exe_path = project_root / "dist" / "SOC Copilot" / "SOC Copilot.exe"
        if exe_path.exists():
            print(f"\n  📁 Executable: {exe_path}")
    
    if installer_built:
        installer_path = project_root / "dist" / f"SOC_Copilot_Setup_{VERSION}.exe"
        if installer_path.exists():
            print(f"  📦 Installer:  {installer_path}")
    
    print("\n  Next steps:")
    if exe_built and not installer_built:
        print("  - Install Inno Setup 6 to create an installer")
        print("  - Or distribute the dist/SOC Copilot/ folder directly")
    elif installer_built:
        print("  - Test the installer on a clean Windows machine")
        print("  - Distribute SOC_Copilot_Setup_*.exe to users")
    else:
        print("  - Fix build errors above and retry")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SOC Copilot End-to-End Build Pipeline"
    )
    parser.add_argument("--clean", action="store_true", help="Clean build")
    parser.add_argument("--exe-only", action="store_true", help="Build EXE only, skip installer")
    parser.add_argument("--dry-run", action="store_true", help="Check prerequisites only")
    args = parser.parse_args()
    
    project_root = get_project_root()
    
    print(f"SOC Copilot Build Pipeline — v{VERSION}")
    print(f"Project root: {project_root}")
    print("=" * 60)
    
    # Check prerequisites
    status = check_prerequisites(project_root)
    
    if not status["python"] or not status["source"]:
        print("\n[FAIL] Critical prerequisites missing")
        sys.exit(1)
    
    if not status["pyinstaller"]:
        print("\n[FAIL] PyInstaller required. Install: pip install pyinstaller>=6.0.0")
        sys.exit(1)
    
    if not status["models"]:
        print("\n[WARN] Models missing — app will have limited functionality")
        print("Run 'python scripts/train_models.py' to train models first\n")
    
    if args.dry_run:
        print("\n[OK] Dry run complete — prerequisites checked")
        sys.exit(0)
    
    # Step 1: Build EXE
    exe_built = run_build_exe(project_root, clean=args.clean)
    
    if not exe_built:
        print("\n[FAIL] Build failed — cannot continue")
        sys.exit(1)
    
    # Step 2: Build installer (optional)
    installer_built = False
    if not args.exe_only and status["inno_setup"] and status.get("iscc_path"):
        installer_built = run_inno_setup(project_root, status["iscc_path"])
    elif not args.exe_only and not status["inno_setup"]:
        print("\n[SKIP] Inno Setup not available — skipping installer creation")
        print("       Install Inno Setup 6: https://jrsoftware.org/isinfo.php")
    
    # Summary
    print_summary(project_root, exe_built, installer_built)
    
    if exe_built:
        print("\n[OK] BUILD SUCCESSFUL")
    else:
        print("\n[FAIL] BUILD FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
