import subprocess
import sys
import os
import shutil
from pathlib import Path

# Run this script to package the app in the terminal
# .\.venv\Scripts\python.exe package_app.py

def build():
    print("====================================================")
    print("   STANDALONE BUILDER: EXE PACKAGING SCRIPT")
    print("====================================================\n")

    build_root = Path("MO2 Hardlink Builder")
    work_path = build_root / "build"
    
    # 1. Clean previous builds
    for folder in ['build', 'dist', str(build_root)]:
        if os.path.exists(folder):
            print(f"[*] Cleaning old {folder} folder...")
            try:
                shutil.rmtree(folder)
            except:
                pass
    
    # Clear spec file in root if any
    for spec in Path(".").glob("*.spec"):
        os.remove(spec)

    # 2. Build Wrapper Template First
    print("[*] Pre-compiling wrapper template...")
    scripts_abs = os.path.abspath("Scripts")
    wrapper_src = scripts_abs + "/wrapper_payload.py"
    wrapper_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "wrapper_template",
        "--distpath", scripts_abs,
        "--workpath", str(work_path / "wrapper"),
        "--specpath", str(build_root),
        "--clean",
        wrapper_src
    ]
    
    try:
        subprocess.run(wrapper_cmd, check=True, capture_output=True)
        print("[SUCCESS] Wrapper template compiled.")
    except Exception as e:
        print(f"[!] Warning: Could not pre-compile wrapper: {e}")

    # 3. Build main app command
    print("[*] Running PyInstaller for main app...")
    
    # We use sys.executable -m PyInstaller to ensure we use the same environment
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "MO2_hardlink_builder",
        "--clean",
        "--distpath", str(build_root),
        "--workpath", str(work_path),
        "--specpath", str(build_root),
        "--add-data", f"{scripts_abs};Scripts",
        "--hidden-import", "tqdm",
        "--hidden-import", "filecmp",
        "standalone_build_deploy.py"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\n[ERROR] PyInstaller failed with exit code {result.returncode}")
            print("--- STDERR ---")
            print(result.stderr)
            print("--- STDOUT ---")
            print(result.stdout)
            return

        print("\n[SUCCESS] Packaging complete!")
        print(f"[*] Everything generated is in: {os.path.abspath(build_root)}")
        print(f"[*] Your executable is: {os.path.abspath(build_root / 'MO2_hardlink_builder.exe')}")
        print("\n[NOTE] The 'output' folder will be created automatically in the same folder as the EXE when you run it.")
    except Exception as e:
        print(f"\n[ERROR] Packaging failed: {e}")

if __name__ == "__main__":
    build()
