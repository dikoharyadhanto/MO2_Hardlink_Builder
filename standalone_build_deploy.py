import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess
import webbrowser
import json
import datetime
import time

# Resolve internal paths for bundling
if getattr(sys, 'frozen', False):
    # PyInstaller temp folder
    bundle_dir = Path(sys._MEIPASS)
else:
    bundle_dir = Path(__file__).parent

# Add Scripts directory to path for imports
scripts_path = bundle_dir / "Scripts"
if scripts_path.exists():
    sys.path.append(str(scripts_path))
else:
    # Diagnostic print (hidden in production unless crash)
    print(f"[DEBUG] Scripts path NOT found at: {scripts_path}")

# Import logic engines directly
try:
    print(f"[*] DEBUG: Attempting to import modules from: {scripts_path}")
    from scanner_engine import ScannerEngine
    from linker_executor import LinkerExecutor
    from cleaner_engine import CleanerEngine
    from profile_sync import ProfileSync
    from verification_engine import VerificationEngine
except Exception as e:
    # Fallback and log the error
    import traceback
    error_details = traceback.format_exc()
    print(f"[!] Critical Import Failure:\n{error_details}")
    ScannerEngine = None
    LinkerExecutor = None
    CleanerEngine = None
    ProfileSync = None
    VerificationEngine = None
    _import_error = f"{str(e)}\n\n{error_details}"
else:
    _import_error = None

def get_base_path():
    """Detects the base path for config/output storage (EXE vs Script)."""
    if getattr(sys, 'frozen', False):
        # Running as packaged EXE
        return Path(sys.executable).parent
    # Running as Python script
    return Path(__file__).parent

def load_config():
    """Loads stored paths from builder_config.json."""
    base = get_base_path()
    config_file = base / "builder_config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config_data):
    """Saves paths to builder_config.json."""
    base = get_base_path()
    config_file = base / "builder_config.json"
    try:
        # Load existing to avoid overwriting unrelated data if any
        existing = load_config()
        existing.update(config_data)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=4)
    except Exception as e:
        print(f"[!] Warning: Could not save config: {e}")

# --- UNIVERSAL GAME MAPPING ---
# Format: "ExecutableName.exe": {"docs": "DocsFolderName", "appdata": "AppDataFolderName", "name": "GameDisplayName", "ini_prefix": "INIPrefix", "appid": "SteamAppID"}
GAME_MAPPING = {
    "SkyrimSE.exe": {"docs": "Skyrim Special Edition", "appdata": "Skyrim Special Edition", "name": "Skyrim Special Edition", "ini_prefix": "Skyrim", "appid": "489830"},
    "Skyrim.exe": {"docs": "Skyrim", "appdata": "Skyrim", "name": "Skyrim VR / Legendary", "ini_prefix": "Skyrim", "appid": "72850"},
    "Starfield.exe": {"docs": "Starfield", "appdata": "Starfield", "name": "Starfield", "ini_prefix": "Starfield", "appid": "1716740"},
    "Fallout4.exe": {"docs": "Fallout4", "appdata": "Fallout4", "name": "Fallout 4", "ini_prefix": "Fallout4", "appid": "377160"},
    "Fallout3.exe": {"docs": "Fallout3", "appdata": "Fallout3", "name": "Fallout 3", "ini_prefix": "Fallout3", "appid": "22300"},
    "FalloutNV.exe": {"docs": "FalloutNV", "appdata": "FalloutNV", "name": "Fallout New Vegas", "ini_prefix": "FalloutNV", "appid": "22380"},
    "Oblivion.exe": {"docs": "Oblivion", "appdata": "Oblivion", "name": "Oblivion", "ini_prefix": "Oblivion", "appid": "22330"},
    "TESV.exe": {"docs": "Skyrim", "appdata": "Skyrim", "name": "Skyrim", "ini_prefix": "Skyrim", "appid": "72850"},
    "EnderalSE.exe": {"docs": "Enderal Special Edition", "appdata": "Enderal Special Edition", "name": "Enderal Special Edition", "ini_prefix": "Enderal", "appid": "976620"},
}

def get_path_ui(title, initialdir=None):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title, initialdir=initialdir)
    root.destroy()
    return path

def show_msg(title, text):
    """Shows an info message box safely without hanging."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo(title, text)
        root.destroy()
    except:
        print(f"\n[{title}] {text}")

def ask_confirm(title, text):
    """Shows a yes/no dialog safely."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        res = messagebox.askyesno(title, text)
        root.destroy()
        return res
    except:
        return input(f"\n[?] {text} (y/n): ").lower().startswith('y')

def is_inside(child, parent):
    """Checks if a path is inside another path."""
    try:
        child_p = Path(child).resolve()
        parent_p = Path(parent).resolve()
        return parent_p in child_p.parents or child_p == parent_p
    except:
        return False

def is_project_path(path):
    """Checks if a path is inside or is the tool's own project directory."""
    return is_inside(path, get_base_path())

def validate_mo2_path(path):
    if is_project_path(path):
        return False, "FORBIDDEN: You cannot select the tool's own folder as the MO2 path!"
    
    p = Path(path)
    if not p.exists(): return False, "Path does not exist."
    # Check for profiles folder or ModOrganizer.exe
    if (p / "profiles").exists() or (p / "ModOrganizer.exe").exists():
        return True, "Valid"
    return False, "This does not look like a Mod Organizer 2 folder (missing 'profiles' or 'ModOrganizer.exe')."

def validate_game_path(path):
    """Validates the original game installation folder and identifies the game."""
    if is_project_path(path):
        return False, "FORBIDDEN: You cannot select the tool's own folder as the Game path!", None
        
    p = Path(path)
    if not p.exists(): return False, "Path does not exist.", None
    
    for exe, info in GAME_MAPPING.items():
        if (p / exe).exists():
            return True, "Valid", info
            
    return False, "This does not look like a supported game installation folder (Game executable not found).", None

def validate_sa_path(sa_path, mo2_path, steam_path):
    if is_project_path(sa_path):
        return False, "FORBIDDEN: You cannot select the tool's own folder as the Standalone destination!"
        
    sa_p = Path(sa_path).resolve()
    mo2_p = Path(mo2_path).resolve()
    steam_p = Path(steam_path).resolve()

    # 1. Absolute Path Protection (Source Folders)
    if is_inside(sa_p, mo2_p) or sa_p == mo2_p:
        return False, "FORBIDDEN: Standalone folder cannot be INSIDE or IS the MO2 folder!"
    if is_inside(mo2_p, sa_p):
        return False, "FORBIDDEN: You cannot select a parent of your MO2 folder as the Standalone destination!"

    if is_inside(sa_p, steam_p) or sa_p == steam_p:
        return False, "FORBIDDEN: Standalone folder cannot be INSIDE or IS your Original Game folder!"
    if is_inside(steam_p, sa_p):
        return False, "FORBIDDEN: You cannot select a parent of your Game installation (like Steam root) as the Standalone destination!"

    # 2. Standalone Identity Check (Allows bypass for rebuilds)
    standalone_markers = ["standalone_metadata", "_profile", "_Profile_Backup"]
    is_standalone = any((sa_p / m).exists() for m in standalone_markers)

    # 3. System Corruption Heuristics (Blocked unless recognized as our Standalone)
    if not is_standalone:
        # Steam/Client Root markers
        client_indicators = ["steam.exe", "Steam.dll", "Galaxy64.dll", "Galaxy.dll"]
        if any((sa_p / indicator).exists() for indicator in client_indicators):
             return False, "DANGER: This folder appears to be a Steam/GOG Client installation directory. Blocked for safety."
        
        # Game system markers
        game_indicators = ["steam_api64.dll", "steam_api.dll", "Galaxy64.dll"]
        if any((sa_p / indicator).exists() for indicator in game_indicators):
             return False, "DANGER: This folder contains game system files. To prevent accidental corruption of your original game, this folder is blocked unless it's a pre-existing Standalone (which would have metadata)."

    return True, "Valid"

if __name__ == "__main__":
    def main_menu():
        print("====================================================")
        print("   MO2 HARDLINK BUILDER: DEPLOYMENT MASTER         ")
        print("====================================================\n")

        # --- SETUP: INITIAL PATH COLLECTION ---
        config = load_config()
        
        while True:
            last_mo2 = config.get("mo2_path")
            print(f"[*] STATUS: Awaiting MO2 Installation folder selection...")
            mo_path = get_path_ui("Select MO2 Installation Folder", initialdir=last_mo2)
            if not mo_path: exit()
            
            valid, msg = validate_mo2_path(mo_path)
            if valid:
                mo2_path = mo_path
                save_config({"mo2_path": mo2_path})
                print(f"[*] STATUS: MO2 Path set to: {mo2_path}\n")
                break
            show_msg("Invalid MO2 Path", msg)

        while True:
            print("[*] STATUS: Awaiting Profile configuration...")
            profiles_root = Path(mo2_path) / "profiles"
            if not profiles_root.exists():
                profiles_root = Path(mo2_path)
                
            selected_profile_path = get_path_ui("Select your MO2 Profile folder", initialdir=str(profiles_root))
            if not selected_profile_path: 
                print("[!] Selection cancelled. Exiting...")
                exit()
            
            # Strict Validation: Must be inside mo2_path/profiles
            if is_inside(selected_profile_path, profiles_root):
                profile_name = Path(selected_profile_path).name
                print(f"[*] STATUS: MO2 Profile set to: {profile_name}\n")
                break
            else:
                show_msg("Invalid Profile Location", 
                        f"FORBIDDEN: The profile you selected is NOT inside your MO2 profiles folder!\n\n"
                        f"Please select a folder inside:\n{profiles_root}")

        while True:
            last_game = config.get("game_path")
            print("[*] STATUS: Awaiting Original Game installation folder selection...")
            st_path = get_path_ui("Select Original Game Folder (Steam/GOG/Epic)", initialdir=last_game)
            if not st_path: exit()
            
            valid, msg, game_info = validate_game_path(st_path)
            if valid:
                game_path = st_path
                save_config({"game_path": game_path})
                print(f"[*] STATUS: Game detected: {game_info['name']}")
                print(f"[*] STATUS: Game Path set to: {game_path}\n")
                break
            show_msg("Invalid Game Path", msg)

        while True:
            print("[*] STATUS: Awaiting STANDALONE destination folder selection...")
            # Standalone build always starts from home as requested
            sa_path_input = get_path_ui("Select STANDALONE Destination Folder", initialdir=str(Path.home()))
            if not sa_path_input: exit()
            
            valid, msg = validate_sa_path(sa_path_input, mo2_path, game_path)
            if valid:
                standalone_path = sa_path_input
                print(f"[*] STATUS: Standalone Path set to: {standalone_path}\n")
                break
            show_msg("Forbidden Folder", msg)

        mo2_p = Path(mo2_path).resolve()
        sa_p = Path(standalone_path).resolve()
        game_p = Path(game_path).resolve()
        
        # Identity to pass to sub-scripts
        docs_name = game_info['docs']
        appdata_name = game_info['appdata']
        ini_prefix = game_info['ini_prefix']
        game_appid = game_info['appid']
        game_exe_name = next(k for k, v in GAME_MAPPING.items() if v['name'] == game_info['name'])

        base_path = get_base_path()
        output_dir = base_path / "output"
        output_dir.mkdir(exist_ok=True)
        
        if not all([ScannerEngine, LinkerExecutor, CleanerEngine, ProfileSync]):
            show_msg("Critical Error", f"Internal logic engines could not be loaded.\n\nERROR:\n{_import_error}")
            exit()

        while True:
            print("\n" + "="*50)
            print(" MAIN MENU - SELECT AN OPERATION:")
            print("="*50)
            print("1. Build Standalone (Full Deployment)")
            print("2. Clean Standalone Only & Restore original Settings/Saves")
            print("3. Import / Export Save (Documents <-> MO2 Profile)")
            print("4. Exit")
            print("-" * 50)
            
            choice = input("[?] Choose option (1-4): ").strip()

            if choice == '1':
                # --- OPTION 1: FULL BUILD ---
                vanilla_mode = 'copy'
                use_hardlink = ask_confirm("Efficiency Options", 
                    "Use Hardlinks for Vanilla files?\n\n"
                    "Advantage: Saves ~15GB disk space.\n"
                    "Requirement: Steam and Standalone folders MUST be on the same Drive.")

                if use_hardlink:
                    if game_p.anchor.lower() == sa_p.anchor.lower():
                        vanilla_mode = 'link'
                    else:
                        retry = ask_confirm("Drive Warning", "ERROR: Different Drives! Continue using COPY mode?")
                        if not retry: continue
                        vanilla_mode = 'copy'

                if mo2_p in sa_p.parents or mo2_p == sa_p:
                    show_msg("CRITICAL SECURITY", "Standalone folder cannot be inside the MO2 folder!")
                    continue
                
                if sa_p == game_p:
                    show_msg("CRITICAL SECURITY", "Standalone folder cannot be your Original Game folder!")
                    continue

                if ask_confirm("Confirm Build", f"Start Full Deployment to:\n{sa_p}?\n\n(Folder will be cleaned first)"):
                    print("\n>>> STARTING FULL DEPLOYMENT...")
                    try:
                        # --- STAGE 1: PRE-CLEAN SAFETY GUARD (Export) ---
                        print("\n[*] PRE-CLEAN SAFETY CHECK: Checking for existing saves...")
                        metadata_path = sa_p / "standalone_metadata" / "standalone_metadata.json"
                        save_path = sa_p / "_profile" / "Documents" / "My Games" / docs_name / "Saves"
                        
                        has_saves = False
                        if save_path.exists():
                            has_saves = any(f.suffix.lower() in ['.ess', '.skse'] for f in save_path.iterdir() if f.is_file())

                        export_profile = profile_name # Default
                        
                        if has_saves:
                            print(f"[!] {len([f for f in save_path.iterdir() if f.is_file()])} saves detected in Standalone folder.")
                            
                            # Determine Original Profile from Metadata
                            metadata_valid = False
                            if metadata_path.exists():
                                try:
                                    with open(metadata_path, 'r', encoding='utf-8') as f:
                                        m_data = json.load(f)
                                        if "build_info" in m_data and "mo2_profile" in m_data["build_info"]:
                                            export_profile = m_data["build_info"]["mo2_profile"]
                                            print(f"[*] Original profile identified from metadata: [{export_profile}]")
                                            metadata_valid = True
                                        else:
                                            print("[!] Metadata missing 'mo2_profile' field.")
                                except Exception as e:
                                    print(f"[!] Error reading metadata: {e}")
                            
                            if not metadata_valid:
                                error_msg = (
                                    "CRITICAL: Metadata missing or broken!\n\n"
                                    "Saves were detected in the standalone folder, but the source MO2 profile is unknown.\n\n"
                                    "Please secure your save files manually before rebuilding to prevent data loss.\n"
                                    f"Location: {save_path}"
                                )
                                show_msg("Security Block: Save Safety", error_msg)
                                print(f"\n[ABORTED] {error_msg.replace('\\n', ' ')}")
                                continue

                            if ask_confirm("Save Export Guard", f"Standalone saves detected.\nExport (Backup) to original profile [{export_profile}] before cleaning?"):
                                print(f"[*] (Copying / Backup) Exporting saves from Standalone -> Profile [{export_profile}]...")
                                p_sync_export = ProfileSync(mo2_p, export_profile, sa_p, docs_name, appdata_name, ini_prefix, game_name=game_info['name'], portable_mode=True)
                                try:
                                    if p_sync_export.sync_saves_to_mo2():
                                        print("[SUCCESS] Saves safely COPIED to MO2.")
                                    else:
                                        if not ask_confirm("Force Proceed?", "Save sync was skipped or encountered an issue. Proceed with CLEANING anyway? (Saves will be lost!)"):
                                            continue
                                except Exception as e:
                                    print(f"[!] Save export failed: {e}")
                                    if not ask_confirm("Force Proceed?", "Could not export saves. Proceed with CLEANING anyway? (Saves will be lost!)"):
                                        continue
                            else:
                                print("[*] Export skipped by user. Proceeding to clean...")
                        else:
                            print("[*] No saves found. Proceeding silently.")

                        # --- STAGE 2: CLEAN ---
                        print("\n[*] (Absolute Fresh Start) Cleaning Standalone folder...")
                        cleaner = CleanerEngine(sa_p, mo2_p, game_p, docs_name, appdata_name, game_name=game_info['name'], profile_name=profile_name, portable_mode=True)
                        is_safe, msg = cleaner.check_safety()
                        if is_safe:
                            cleaner.restore_profiles() # Restore original settings if any
                            cleaner.total_cleanup() # WIPE standalone folder
                        else:
                            show_msg("Security Block", msg)
                            continue

                        # 2.5 PREPARE METADATA FOLDER
                        output_dir = sa_p / "standalone_metadata"
                        output_dir.mkdir(parents=True, exist_ok=True)

                        # 3. SCAN
                        print("\n[*] Scanning Mods...")
                        scanner = ScannerEngine(mo2_p, profile_name)
                        scanner.output_dir = output_dir
                        scanner.output_manifest = output_manifest = output_dir / "mapping_manifest.json"
                        scanner.build_mapping()

                        # 4. LINK
                        print("\n[*] Deploying Files...")
                        linker = LinkerExecutor(sa_p, game_p)
                        linker.output_dir = output_dir
                        linker.manifest_file = output_manifest
                        linker.report_file = output_dir / "execution_report.json"
                        
                        # Initial vanilla clone
                        linker.initial_vanilla_clone(mode=vanilla_mode)
                        linker.execute_mapping(clean=False)

                        # --- STAGE 5: SYNC CONFIG (INIs & Plugins) ---
                        print("\n[*] Injecting Profile Configuration (Portable)...")
                        p_sync = ProfileSync(mo2_p, profile_name, sa_p, docs_name, appdata_name, ini_prefix, game_name=game_info['name'], portable_mode=True)
                        p_sync.deploy_mo2_profile() # Handles INIs, Plugins, Loadorder
                        
                        # --- STAGE 6: FINAL IMPORT (Saves) ---
                        print(f"\n[*] FINAL STAGE: Importing saves from MO2 Profile [{profile_name}] -> Standalone...")
                        try:
                            p_sync.push_saves_to_docs()
                            print("[SUCCESS] Saves safely IMPORTED (Copied) to Standalone.")
                        except Exception as e:
                            print(f"[!] Warning: Could not import saves: {e}")

                        p_sync.clean_custom_save_path()

                        # --- STAGE 5.1: UNIVERSAL MULTI-HIJACK DEPLOYMENT ---
                        print("\n[*] Implementing Universal Hijack for Total Isolation...")
                        
                        # Identify all relevant EXEs to hijack dynamically
                        potential_targets = [
                            game_exe_name,
                            f"{Path(game_exe_name).stem}Launcher.exe",
                        ]
                        if ini_prefix:
                            potential_targets.append(f"{ini_prefix}Launcher.exe")
                        
                        # Standard mod loaders for various Bethesda games
                        common_loaders = [
                            "skse64_loader.exe", "f4se_loader.exe", "sfse_loader.exe", 
                            "nvse_loader.exe", "obse_loader.exe", "skse_loader.exe", 
                            "mgexe.exe", "mwse.exe"
                        ]
                        potential_targets.extend(common_loaders)
                        
                        # Adaptive: Scan for anything ending in "Launcher.exe" in the SA root
                        try:
                            for item in sa_p.iterdir():
                                if item.is_file() and item.name.lower().endswith("launcher.exe"):
                                    potential_targets.append(item.name)
                        except: pass

                        # Filter unique non-empty targets
                        # CRITICAL FIX: DO NOT hijack Main Game EXEs (they contain version info Loaders need)
                        game_executables = [
                            game_exe_name.lower(), 
                            f"{Path(game_exe_name).stem}Launcher.exe".lower(),
                            "launcher.exe",
                            "skyrimlauncher.exe",
                            "falloutlauncher.exe"
                        ]
                        if ini_prefix:
                            game_executables.append(f"{ini_prefix}Launcher.exe".lower())
                        
                        critical_exes = []
                        for t in potential_targets:
                            if t and t.lower() not in game_executables:
                                if t not in critical_exes:
                                    critical_exes.append(t)
                        
                        hijacked_count = 0
                        wrapper_src_py = scripts_path / "wrapper_payload.py"
                        wrapper_template_exe = scripts_path / "wrapper_template.exe"
                        
                        # No longer scanning for PyInstaller at runtime - we use pre-compiled template
                        has_template = wrapper_template_exe.exists()
                        if has_template:
                            print(f"    [*] Using pre-compiled wrapper template: {wrapper_template_exe}")
                        else:
                            print(f"    [!] Warning: Pre-compiled wrapper template NOT found. Falling back to .bat mode.")

                        for target_exe in critical_exes:
                            target_path = sa_p / target_exe
                            if not target_path.exists():
                                continue
                                
                            original_name = f"_{target_exe.replace('.exe', '')}_original.exe"
                            original_path = sa_p / original_name
                            
                            # Perform Rename
                            if original_path.exists():
                                original_path.unlink() # Cleanup old original if exists
                            target_path.rename(original_path)
                            
                            # Hide original
                            try:
                                subprocess.run(['attrib', '+h', str(original_path)], check=True)
                            except: pass
                            
                            print(f"    -> Hijacked {target_exe} (Original renamed to {original_name})")
                            hijacked_count += 1
                            
                            # Deploy Wrapper
                            if has_template:
                                # Use Pre-compiled EXE (Fast & Reliable)
                                try:
                                    shutil.copy2(wrapper_template_exe, sa_p / target_exe)
                                    print(f"    -> Deployed EXE wrapper for {target_exe}")
                                except Exception as e:
                                    print(f"    [!] Error copying EXE template: {e}")
                                    # Fallback to .bat
                                    with open(sa_p / target_exe.replace(".exe", ".bat"), "w") as f:
                                        f.write(f"@echo off\npython Wrapper_{target_exe.replace('.exe', '.py')}\n")
                            elif wrapper_src_py.exists():
                                # Fallback to .bat
                                shutil.copy2(wrapper_src_py, sa_p / f"Wrapper_{target_exe.replace('.exe', '.py')}")
                                with open(sa_p / target_exe.replace(".exe", ".bat"), "w") as f:
                                    f.write(f"@echo off\npython Wrapper_{target_exe.replace('.exe', '.py')}\n")
                                print(f"    -> Deployed .bat fallback for {target_exe}")
                            else:
                                print(f"    [!] Error: wrapper_template.exe AND wrapper_payload.py missing for {target_exe}")

                        # --- STAGE 5.1.5: GENERATE LAUNCH INSTRUCTIONS ---
                        print("\n[*] Generating Launch Instructions...")
                        try:
                            # Detect which loader to point to
                            main_loader = next((t for t in critical_exes if "loader" in t.lower()), critical_exes[0] if critical_exes else "the original loader")
                            loader_ext = ".exe" if has_template else ".bat"
                            loader_final = main_loader.replace(".exe", loader_ext)
                            
                            launch_info = [
                                "=== STANDALONE BUILD: LAUNCH INSTRUCTIONS ===",
                                "",
                                f"To play the game, run: {loader_final}",
                                "",
                                "WHY ARE FILES RENAMED?",
                                "To ensure total isolation from your main Skyrim installation every",
                                "original executable has been renamed (prefixed with '_') and hidden.",
                                "A small 'wrapper' has been created to set up the isolated environment",
                                "whenever you launch the game.",
                                "",
                                "IMPORTANT:",
                                "- DO NOT launch the game via the '_' prefixed EXEs directly.",
                                f"- Always use {loader_final} to ensure your saves and settings remain portable.",
                                "",
                                f"Build Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                f"Profile: {profile_name}"
                            ]
                            
                            with open(sa_p / "How to Launch.txt", "w", encoding='utf-8') as f:
                                f.write("\n".join(launch_info))
                            print(f"[SUCCESS] Instructions generated: {sa_p / 'How to Launch.txt'}")
                        except Exception as e:
                            print(f"[!] Warning: Could not generate launch instructions: {e}")

                        print(f"[SUCCESS] Multi-Hijack complete. {hijacked_count} executables isolated.")
                        
                        # --- STAGE 5.2: CLEANUP BUILD ARTIFACTS ---
                        print("[*] Organizing build artifacts (.spec files)...")
                        try:
                            # Small delay to allow PyInstaller to release file locks
                            time.sleep(1)
                            potential_spec_sources = [output_dir, base_path / "output"]
                            for source in potential_spec_sources:
                                if source.exists():
                                    for spec_file in source.glob("*.spec"):
                                        try:
                                            # Move to metadata folder
                                            target_spec = output_dir / spec_file.name
                                            if target_spec != spec_file:
                                                shutil.copy2(spec_file, target_spec)
                                                spec_file.unlink()
                                        except Exception as per_file_e:
                                            print(f"    [-] Could not move {spec_file.name}: {per_file_e}")
                            print("[SUCCESS] Build metadata organized.")
                        except Exception as e:
                            print(f"[!] Warning: Artifact cleanup encountered an issue: {e}")

                        # --- STAGE 6: STANDALONE ISOLATION ---
                        with open(sa_p / "steam_appid.txt", "w") as f:
                            f.write(game_appid)
                            
                        # --- STAGE 8: GENERATE METADATA ---
                        print("\n[*] Generating Standalone Metadata...")
                        try:
                            metadata = {
                                "build_info": {
                                    "game_name": game_info['name'],
                                    "mo2_profile": profile_name,
                                    "build_timestamp": datetime.datetime.now().isoformat(),
                                    "portable_mode": True
                                },
                                "paths": {
                                    "standalone_root": str(sa_p),
                                    "local_appdata": str(p_sync.win_appdata),
                                    "local_documents": str(p_sync.win_docs),
                                    "local_saves": str(p_sync.win_docs / "Saves"),
                                    "original_mo2": str(mo2_p),
                                    "original_game": str(game_p)
                                },
                                "game_config": {
                                    "ini_prefix": ini_prefix,
                                    "appdata_name": appdata_name,
                                    "docs_name": docs_name,
                                    "manifest_file": str(output_manifest)
                                }
                            }
                            with open(output_dir / "standalone_metadata.json", "w", encoding='utf-8') as f:
                                json.dump(metadata, f, indent=4)
                            print("[SUCCESS] Metadata generated: standalone_metadata/standalone_metadata.json")
                        except Exception as e:
                            print(f"[!] Error generating metadata: {e}")

                        show_msg("Success", "Standalone Deployment Finished Successfully!")

                    except Exception as e:
                        print(f"\n[CRITICAL ERROR DURING BUILD] {e}")
                        show_msg("Build Failed", str(e))
                        
                    # --- STAGE 6: VERIFICATION ENGINE ---
                    verification_results = {}
                    try:
                        print("\n>>> RUNNING: Comprehensive Verification...")
                        verifier = VerificationEngine()
                        verification_results = verifier.run_all_checks(
                            manifest_path=output_manifest,
                            standalone_path=sa_p,
                            mo2_profile_path=mo2_p / "profiles" / profile_name,
                            appdata_path=p_sync.win_appdata,
                            doc_save_path=p_sync.win_docs,
                            ini_prefix=ini_prefix,
                            run_timestamp=p_sync.run_timestamp
                        )
                        print("[SUCCESS] Verification complete.")
                    except Exception as e:
                        print(f"[!] Verification failed: {e}")

                    # --- STAGE 7: GENERATE INTERACTIVE REPORT ---
                    print("\n>>> RUNNING: Generating Interactive HTML Report...")
                    try:
                        from report_generator import ReportGenerator
                        gen = ReportGenerator(
                            manifest_path=str(output_dir / "mapping_manifest.json"), 
                            report_path=str(output_dir / "execution_report.json"),
                            output_html=str(output_dir / "build_report.html")
                        )
                        gen.generate(verification_results)
                        
                        report_file = output_dir / "build_report.html"
                        print(f"\n[SUCCESS] Deployment complete! Report generated: {report_file}")
                        
                        if ask_confirm("Open Report", "Build finished! Would you like to open the HTML report in your browser?"):
                            webbrowser.open(str(report_file))
                            
                    except Exception as e:
                        print(f"[!] Failed report: {e}")
                
                input("\n>>> Press Enter to return to Main Menu...")

            elif choice == '2':
                # --- OPTION 2: CLEAN ONLY ---
                if ask_confirm("Confirm Clean", f"Clean Standalone Folder?\nTarget: {sa_p}"):
                    print("\n[*] Cleaning Standalone folder...")
                    try:
                        # ENFORCED PORTABLE MODE for simplicity
                        is_portable = True 
                        cleaner = CleanerEngine(sa_p, mo2_p, game_p, docs_name, appdata_name, portable_mode=is_portable)
                        is_safe, msg = cleaner.check_safety()
                        if is_safe:
                            # --- PRE-CLEAN SAFETY GUARD (Export) ---
                            print("\n[*] PRE-CLEAN SAFETY CHECK: Checking for existing saves...")
                            metadata_path = sa_p / "standalone_metadata" / "standalone_metadata.json"
                            save_path = sa_p / "_profile" / "Documents" / "My Games" / docs_name / "Saves"
                            
                            has_saves = False
                            if save_path.exists():
                                has_saves = any(f.suffix.lower() in ['.ess', '.skse'] for f in save_path.iterdir() if f.is_file())

                            export_profile = profile_name # Default
                            
                            if has_saves:
                                print(f"[!] {len([f for f in save_path.iterdir() if f.is_file()])} saves detected in Standalone folder.")
                                
                                # Determine Original Profile from Metadata
                                metadata_valid = False
                                if metadata_path.exists():
                                    try:
                                        with open(metadata_path, 'r', encoding='utf-8') as f:
                                            m_data = json.load(f)
                                            if "build_info" in m_data and "mo2_profile" in m_data["build_info"]:
                                                export_profile = m_data["build_info"]["mo2_profile"]
                                                print(f"[*] Original profile identified from metadata: [{export_profile}]")
                                                metadata_valid = True
                                            else:
                                                print("[!] Metadata missing 'mo2_profile' field.")
                                    except Exception as e:
                                        print(f"[!] Error reading metadata: {e}")

                                if not metadata_valid:
                                    error_msg = (
                                        "CRITICAL: Metadata missing or broken!\n\n"
                                        "Saves were detected in the standalone folder, but the source MO2 profile is unknown.\n\n"
                                        "Please secure your save files manually before cleaning to prevent data loss.\n"
                                        f"Location: {save_path}"
                                    )
                                    show_msg("Security Block: Save Safety", error_msg)
                                    print(f"\n[ABORTED] {error_msg.replace('\\n', ' ')}")
                                    continue

                                if ask_confirm("Save Export Guard", f"Standalone saves detected.\nExport (Backup) to original profile [{export_profile}] before cleaning?"):
                                    print(f"[*] (Copying / Backup) Exporting saves from Standalone -> Profile [{export_profile}]...")
                                    p_sync_export = ProfileSync(mo2_p, export_profile, sa_p, docs_name, appdata_name, ini_prefix, game_name=game_info['name'], portable_mode=True)
                                    try:
                                        p_sync_export.sync_saves_to_mo2()
                                        print("[SUCCESS] Saves safely COPIED to MO2.")
                                        
                                        # --- NEW: CONSISTENT REPORTING ---
                                        print("[*] Running Post-Sync Verification...")
                                        verifier = VerificationEngine()
                                        verification_results = verifier.run_all_checks(
                                            mo2_profile_path=mo2_p / "profiles" / export_profile,
                                            appdata_path=p_sync_export.win_appdata,
                                            doc_save_path=p_sync_export.win_docs,
                                            ini_prefix=ini_prefix,
                                            run_timestamp=p_sync_export.run_timestamp
                                        )
                                        
                                        # Generate report if quarantines exist
                                        if verification_results.get("quarantined_items") or verification_results.get("has_historic_quarantine"):
                                            print("[!] Quarantined items detected. Generating report...")
                                            from report_generator import ReportGenerator
                                            # Save Clean report to parent folder because Standalone folder will be deleted
                                            report_file = sa_p.parent / "clean_report.html"
                                            gen = ReportGenerator(
                                                report_path=str(sa_p / "standalone_metadata" / "execution_report.json"),
                                                output_html=str(report_file)
                                            )
                                            gen.generate(verification_results, show_deployment=False)
                                            
                                            if ask_confirm("Open Report", "Quarantined saves detected! Open report now for manual review?"):
                                                webbrowser.open(str(report_file))

                                    except Exception as e:
                                        print(f"[!] Save export failed: {e}")
                                        if not ask_confirm("Force Clean?", "Could not export saves. Proceed with TOTAL DELETION anyway? (Saves will be lost!)"):
                                            continue
                                else:
                                    print("[*] Export skipped by user. Proceeding to clean...")
                            else:
                                print("[*] No standalone saves found. Proceeding silently.")

                            cleaner.restore_profiles()
                            cleaner.total_cleanup()
                            print("\n[SUCCESS] Cleanup and Restore complete.")
                            show_msg("Success", "Standalone folder cleaned and original settings restored.")
                        else:
                            show_msg("Security Block", msg)
                    except Exception as e:
                        print(f"[!] Cleanup failed: {e}")
                        show_msg("Error", str(e))
                
                input("\n>>> Press Enter to return to Main Menu...")

            elif choice == '3':
                # --- OPTION 3: SAVE SYNC ---
                while True:
                    print("\n" + "-"*50)
                    print(" SAVE IMPORT/EXPORT ")
                    print("-" * 50)
                    print("1. Export: Documents -> MO2 Profile (Safe Backup)")
                    print("2. Import: MO2 Profile -> Documents (Ready to Play in MO2)")
                    print("3. Back to Main Menu")
                    print("-" * 50)
                    
                    sub_choice = input("\n[?] Choose operation (1-3): ").strip()
                    
                    if sub_choice == '3':
                        break
                        
                    # Manual Sync in standalone always targets portable folders
                    is_portable = True 
                    
                    try:
                        p_sync = ProfileSync(mo2_p, profile_name, sa_p, docs_name, appdata_name, ini_prefix, game_name=game_info['name'], portable_mode=is_portable)
                        
                        if sub_choice in ['1', '2']:
                            success = False
                            if sub_choice == '1':
                                success = p_sync.sync_saves_to_mo2()
                                source = "Standalone Profile"
                                msg = "Saves exported from Standalone to MO2 profile."
                                report_name = "export_save_report.html"
                            else:
                                success = p_sync.push_saves_to_docs()
                                dest = "Standalone Profile"
                                msg = "Saves imported from MO2 to Standalone."
                                report_name = "import_save_report.html"

                            if not success:
                                print("[*] Operation canceled or no files were found.")
                                continue

                            # --- NEW: CONSISTENT REPORTING ---
                            print("[*] Running Post-Sync Verification...")
                            verifier = VerificationEngine()
                            verification_results = verifier.run_all_checks(
                                mo2_profile_path=mo2_p / "profiles" / profile_name,
                                appdata_path=p_sync.win_appdata,
                                doc_save_path=p_sync.win_docs,
                                ini_prefix=ini_prefix,
                                run_timestamp=p_sync.run_timestamp
                            )
                            
                            # Generate report if quarantines exist
                            if verification_results.get("quarantined_items") or verification_results.get("has_historic_quarantine"):
                                print("[!] Quarantined items detected. Generating report...")
                                from report_generator import ReportGenerator
                                output_dir = sa_p / "standalone_metadata"
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                report_file = output_dir / report_name
                                
                                gen = ReportGenerator(
                                    report_path=str(output_dir / "execution_report.json"), 
                                    output_html=str(report_file)
                                )
                                gen.generate(verification_results, show_deployment=False)
                                
                                if ask_confirm("Open Report", f"{msg}\n\nQuarantined saves detected! Open report now for manual review?"):
                                    webbrowser.open(str(report_file))
                                else:
                                    show_msg("Success", msg)
                            else:
                                show_msg("Success", msg)
                        else:
                            print("[!] Invalid selection.")
                    except Exception as e:
                        print(f"[!] Manual sync failed: {e}")
                        show_msg("Sync Error", f"Operation failed: {str(e)}")

            elif choice == '4':
                print("[!] Exiting...")
                sys.exit(0)
            else:
                print("[!] Invalid choice.")

    main_menu()
