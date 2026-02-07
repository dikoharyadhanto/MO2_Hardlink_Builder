import os
import sys
import subprocess
import time
from pathlib import Path

def launch():
    # 1. Determine local paths
    # If compiled with PyInstaller, sys.executable is the path to the EXE
    # If running as script, Path(__file__).parent is the folder
    if getattr(sys, 'frozen', False):
        exe_path = Path(sys.executable).parent
    else:
        exe_path = Path(__file__).parent

    profile_path = exe_path / "_profile"
    
    # Standard Windows Profile subdirectories
    appdata_local = profile_path / "AppData" / "Local"
    appdata_roaming = profile_path / "AppData" / "Roaming"
    user_docs = profile_path / "Documents"

    # 2. Ensure Standard Folders Exist
    appdata_local.mkdir(parents=True, exist_ok=True)
    appdata_roaming.mkdir(parents=True, exist_ok=True)
    user_docs.mkdir(parents=True, exist_ok=True)
    (user_docs / "My Games").mkdir(parents=True, exist_ok=True)

    # 3. SET ISOLATION ENVIRONMENT
    # We set these ONLY for the child process (the game)
    env = os.environ.copy()
    env['USERPROFILE'] = str(profile_path)
    env['LOCALAPPDATA'] = str(appdata_local)
    env['APPDATA'] = str(appdata_roaming)
    
    # Set TEMP/TMP to isolation folder to prevent leaks
    env['TEMP'] = str(appdata_local / "Temp")
    env['TMP'] = str(appdata_local / "Temp")
    (appdata_local / "Temp").mkdir(parents=True, exist_ok=True)
    
    # Force Documents folder to be recognized correctly by Windows API if possible
    # Note: Modern games usually respect USERPROFILE for the Documents location.
    
    # 4. Find the Original Game Executable
    # We detect our own name and look for the corresponding hidden original
    self_exe = Path(sys.executable).name if getattr(sys, 'frozen', False) else "skse64_loader.exe"
    target_name = f"_{self_exe.replace('.exe', '')}_original.exe"
    found_target = exe_path / target_name
            
    if not found_target.exists():
        # Fallback for script mode testing
        targets = ["_skse_original.exe", "_skyrim_original.exe", "_launcher_original.exe"]
        for t in targets:
            if (exe_path / t).exists():
                found_target = exe_path / t
                break
            
    if not found_target.exists():
        print(f"Error: Could not find the original game executable ({target_name})")
        print(f"Searched in: {exe_path}")
        time.sleep(5)
        return

    # 5. Launch Game
    try:
        print(f"[*] Launching Isolated Game: {found_target}...")
        subprocess.Popen([str(found_target)] + sys.argv[1:], env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("[SUCCESS] Game process started. Isolation active.")
    except Exception as e:
        print(f"Error launching game: {e}")
        time.sleep(10)

if __name__ == "__main__":
    launch()
