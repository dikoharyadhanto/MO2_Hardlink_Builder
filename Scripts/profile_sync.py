import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

class ProfileSync:
    def __init__(self, mo2_path, profile_name, sa_path, docs_name="Skyrim Special Edition", appdata_name="Skyrim Special Edition", ini_prefix="Skyrim", game_name="Skyrim SE", portable_mode=True):
        self.mo2_path = Path(mo2_path).resolve()
        self.profile_name = profile_name
        self.profile_dir = self.mo2_path / "profiles" / profile_name
        self.sa_path = Path(sa_path).resolve()
        self.ini_prefix = ini_prefix
        self.portable_mode = portable_mode
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Lokasi Target (Standard vs Portable)
        if self.portable_mode:
            # Redirect to local folder inside Standalone
            # Standard: [USERPROFILE]/Documents/My Games/[GameName]
            # Standard: [USERPROFILE]/AppData/Local/[GameName]
            self.win_docs = self.sa_path / "_profile" / "Documents" / "My Games" / docs_name
            self.win_appdata = self.sa_path / "_profile" / "AppData" / "Local" / appdata_name
            self.win_roaming = self.sa_path / "_profile" / "AppData" / "Roaming" / appdata_name
            print(f"[*] Portable Mode Active: Redirecting profile to {self.sa_path / '_profile'}")
        else:
            self.win_docs = Path(os.path.expanduser(f"~/Documents/My Games/{docs_name}"))
            self.win_appdata = Path(os.environ['LOCALAPPDATA']) / appdata_name
            self.win_roaming = Path(os.environ['APPDATA']) / appdata_name
        
        # Ensure target directories exist
        self.win_docs.mkdir(parents=True, exist_ok=True)
        self.win_appdata.mkdir(parents=True, exist_ok=True)
        self.win_roaming.mkdir(parents=True, exist_ok=True)
        
        # New Dynamic Backup Path in LocalAppData
        self.backup_root = Path(os.environ['LOCALAPPDATA']) / "MO2_Hardlink_Builder" / game_name / profile_name / "Backups"
        if not self.portable_mode:
             self.backup_root.mkdir(parents=True, exist_ok=True)
             
        # Validation: Check if MO2 Profile exists
        if not self.profile_dir.exists():
            print(f"[!] WARNING: MO2 Profile folder not found: {self.profile_dir}")
            print(f"    Check your profile name: '{self.profile_name}'")
            # We don't abort here to allow creating it, but we warn the user.

    def _safe_copy(self, src, dst):
        """Helper untuk copy file jika sumbernya ada."""
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        return False

    def _ask_user(self, title, message):
        """Asks user Yes/No safely using Tkinter."""
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            res = messagebox.askyesno(title, message)
            root.destroy()
            return res
        except:
            return input(f"\n[?] {message} (y/n): ").lower().startswith('y')

    def _process_sync(self, src_dir, dst_dir, quarantine_base_name, action_label):
        """Generic sync with conflict resolution using COPY logic and timestamped quarantine."""
        if not src_dir.exists():
            print(f"[!] No saves found in {src_dir} to sync.")
            return False

        # 0. Initial Discovery
        all_files = [item for item in src_dir.iterdir() if item.is_file()]
        if not all_files:
            print(f"[*] Folder is empty: {src_dir}")
            self._ask_user("Sync Notice", f"No save files were found in the source folder:\n{src_dir}")
            return False

        print(f"[*] Found {len(all_files)} files in {src_dir}")
        
        # 0.1 Pre-Sync Confirmation (The missing "Verifikasi")
        confirm_msg = f"Save Sync Operation: {action_label}\n\n" \
                      f"Source: {src_dir}\n" \
                      f"Target: {dst_dir}\n\n" \
                      f"Found {len(all_files)} save files. Proceed with synchronization?\n" \
                      f"(You will be prompted again if conflicts are found)"
        if not self._ask_user(f"Confirm Sync: {action_label}", confirm_msg):
            print("[*] Sync aborted by user.")
            return False

        print(f"[*] Copying saves: {action_label}...")
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Analyze Conflicts
        conflicts = []
        new_files = []
        
        # Normalize paths for case-insensitive comparison and logging
        print(f"[*] Analyzing conflicts in: {dst_dir}")
        for item in src_dir.iterdir():
            if item.is_file():
                target_path = dst_dir / item.name
                if target_path.exists():
                    print(f"    [!] CONFLICT: {item.name} already exists in target.")
                    conflicts.append(item)
                else:
                    new_files.append(item)

        if not conflicts:
            print("    [OK] No file conflicts detected. All files will be copied directly.")

        overwrite = True
        quarantine_dir = None
        
        if conflicts:
            quarantine_name = f"{quarantine_base_name}_{self.run_timestamp}"
            msg = f"Save Conflict Detected during Copy ({action_label})\n\n" \
                  f"Conflict detected for {len(conflicts)} save files in destination.\n\n" \
                  f"Overwrite existing files in destination?\n" \
                  f"YES: Overwrite them (Safe copy mode).\n" \
                  f"NO: Copy to quarantine folder '{quarantine_name}' instead."
            overwrite = self._ask_user(f"Save Sync: {action_label}", msg)
            
            if not overwrite:
                quarantine_dir = dst_dir / quarantine_name
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                print(f"[*] Conflict mode: Quarantine to {quarantine_name}")
                
                # Cleanup old quarantine folders (Limit 5)
                self._prune_quarantine_folders(dst_dir, quarantine_base_name)

        # 2. Execute Copy
        count = 0
        # Copy non-conflicting files
        for item in new_files:
            shutil.copy2(item, dst_dir / item.name)
            count += 1
            
        # Copy conflicting files
        for item in conflicts:
            target_folder = dst_dir if overwrite else quarantine_dir
            shutil.copy2(item, target_folder / item.name)
            count += 1
            
        print(f"[SUCCESS] Processed {count} files (Overwritten: {overwrite}).")
        return True

    def _prune_quarantine_folders(self, root_dir, prefix):
        """Keeps only the 5 most recent quarantine folders for a given prefix."""
        try:
            # Find folders matching pattern (e.g., MO2_import_save_*)
            folders = [d for d in root_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)]
            
            # Sort by name (since it's YYYYMMDD_HHMM, lexicographical sort works perfectly)
            folders.sort(key=lambda x: x.name)
            
            if len(folders) > 5:
                to_delete = folders[:-5] # Keep the last 5
                print(f"[*] Post-Deployment Cleanup: Limit of 5 quarantine folders reached.")
                for folder in to_delete:
                    print(f"    [-] Automatically pruning oldest backup: {folder.name}")
                    shutil.rmtree(folder, ignore_errors=True)
        except Exception as e:
            print(f"[ERROR] Failed to prune old quarantine folders: {e}")

    def _get_saves_folder(self, root_dir):
        """Finds the 'Saves' or 'saves' folder in the given directory."""
        if not root_dir.exists():
            return root_dir / "saves" # Default
        
        # Try finding existing folder (case-insensitive)
        for item in root_dir.iterdir():
            if item.is_dir() and item.name.lower() == "saves":
                return item
        
        return root_dir / "saves" # Default fallback

    def sync_saves_to_mo2(self):
        """COPIES saves from Standalone folder to MO2 Profile."""
        win_saves = self._get_saves_folder(self.win_docs)
        mo2_saves = self._get_saves_folder(self.profile_dir)
        return self._process_sync(win_saves, mo2_saves, "Standalone_Export_save", "Standalone -> MO2 Profile")

    def push_saves_to_docs(self):
        """COPIES saves from MO2 Profile to Standalone folder."""
        mo2_saves = self._get_saves_folder(self.profile_dir)
        win_saves = self._get_saves_folder(self.win_docs)
        return self._process_sync(mo2_saves, win_saves, "MO2_import_save", "MO2 Profile -> Standalone")

    def sync_settings_to_mo2(self):
        """Syncs INIs from Windows Documents back to MO2 Profile."""
        print("[*] Syncing INI files from Windows Documents to MO2 Profile...")
        for ini in ['Skyrim.ini', 'SkyrimPrefs.ini', 'SkyrimCustom.ini']:
            src = self.win_docs / ini
            dst = self.profile_dir / ini
            if self._safe_copy(src, dst):
                print(f"    -> Synced back to MO2: {ini}")

    def clean_custom_save_path(self):
        """Removes SLocalSavePath from [Game]Custom.ini to restore default save location."""
        custom_ini_name = f"{self.ini_prefix}Custom.ini"
        custom_ini = self.win_docs / custom_ini_name
        if not custom_ini.exists():
            return

        print(f"[*] Cleaning {custom_ini_name} (Restoring default save path)...")
        try:
            # Using utf-8-sig to handle potential BOM correctly and prevent corruption
            with open(custom_ini, 'r', encoding='utf-8-sig', errors='ignore') as f:
                lines = f.readlines()

            new_lines = [line for line in lines if "slocalsavepath" not in line.lower()]

            if len(lines) != len(new_lines):
                with open(custom_ini, 'w', encoding='utf-8-sig') as f:
                    f.writelines(new_lines)
                print(f"[SUCCESS] SLocalSavePath removed from {custom_ini_name}.")
            else:
                print(f"[-] No SLocalSavePath found in {custom_ini_name}.")
        except Exception as e:
            print(f"[ERROR] Failed to clean {custom_ini_name}: {e}")

    def backup_original_windows_data(self):
        """Backs up original Windows Save/INI data to the internal backup folder for safety."""
        print("[*] Backing up original game data for safety...")
        
        # Ensure backup root directory exists
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # 1. Backup INIs
        for ini in [f'{self.ini_prefix}.ini', f'{self.ini_prefix}Prefs.ini', f'{self.ini_prefix}Custom.ini']:
            src = self.win_docs / ini
            dst = self.backup_root / ini
            if self._safe_copy(src, dst):
                print(f"    -> Backed up: {ini}")

        # 2. Backup Saves folder
        src_saves = self.win_docs / "Saves"
        dst_saves = self.backup_root / "Saves"
        if src_saves.exists():
            if dst_saves.exists():
                shutil.rmtree(dst_saves) # Clear existing backup to ensure fresh copy
            shutil.copytree(src_saves, dst_saves)
            print("    -> Backed up Saves folder.")
        else:
            print("    -> No Saves folder found to backup.")

        # 3. Backup AppData (Plugins.txt, Loadorder.txt)
        # Note: This part of the original code was backing up the entire AppData folder,
        # which might be too broad. The instruction focused on INIs and Saves.
        # For plugins/loadorder, it's usually just the .txt files.
        # Keeping the original AppData backup logic for now, as the instruction didn't explicitly change it.
        if self.win_appdata.exists():
            app_backup = self.backup_root / "AppData"
            if not app_backup.exists():
                shutil.copytree(self.win_appdata, app_backup)
                print(f"[+] AppData backup complete: {app_backup}")
            else:
                print(f"[-] AppData backup already exists: {app_backup}")


    def deploy_mo2_profile(self):
        """Injects MO2 profile configuration (INIs & Plugins) into the Windows system."""
        print(f"[*] Deploying MO2 profile [{self.profile_dir.name}] configuration...")

        # 1. Deploy INI Files
        for ini in [f'{self.ini_prefix}.ini', f'{self.ini_prefix}Prefs.ini', f'{self.ini_prefix}Custom.ini']:
            src = self.profile_dir / ini
            dst = self.win_docs / ini
            if self._safe_copy(src, dst):
                print(f"    -> Deployed: {ini}")

        # 2. Clean Custom INI (Remove hardcoded save paths)
        self.clean_custom_save_path()

        # 3. Deploy Plugins & Loadorder (to AppData)
        for txt in ['plugins.txt', 'loadorder.txt']:
            src = self.profile_dir / txt
            dst = self.win_appdata / txt
            if self._safe_copy(src, dst):
                print(f"    -> Deployed: {txt}")

        print("[SUCCESS] MO2 Profile configuration is now active.")

def get_folder(title):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return path

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="MO2 Profile Settings & Save Sync Tool")
    parser.add_argument("mo2_path", nargs="?", help="Path to MO2 installation")
    parser.add_argument("profile_name", nargs="?", help="Name of the MO2 profile")
    parser.add_argument("standalone_path", nargs="?", help="Path to Standalone folder")
    parser.add_argument("--docs-name", default="Skyrim Special Edition", help="Documents folder name (e.g., 'Skyrim Special Edition')")
    parser.add_argument("--appdata-name", default="Skyrim Special Edition", help="AppData folder name (e.g., 'Skyrim Special Edition')")
    parser.add_argument("--ini-prefix", default="Skyrim", help="INI prefix (e.g., 'Skyrim', 'Fallout4')")
    parser.add_argument("--game-name", default="Skyrim SE", help="Display name of the game for backup folders")
    parser.add_argument("--pull-only", action="store_true", help="Only pull saves from Docs to MO2")
    parser.add_argument("--push-only", action="store_true", help="Only push saves from MO2 to Docs")
    
    args = parser.parse_args()

    if args.mo2_path and args.profile_name and args.standalone_path:
        sync = ProfileSync(args.mo2_path, args.profile_name, args.standalone_path, args.docs_name, args.appdata_name, args.ini_prefix, game_name=args.game_name)
        if args.pull_only:
            sync.sync_saves_to_mo2()
        elif args.push_only:
            sync.push_saves_to_docs()
        else:
            sync.backup_original_windows_data()
            sync.deploy_mo2_profile()
            print("\n[SUCCESS] Profile Sync complete.")
            print("Please run the game via the Standalone folder.")
    else:
        # UI for manual execution
        try:
            m_path = get_folder("Select MO2 Folder")
            if not m_path: exit()
            
            p_name = input("[?] Enter MO2 Profile Name: ").strip() or "Default"
            
            s_path = get_folder("Select your Standalone Folder")
            if not s_path: exit()

            sync = ProfileSync(m_path, p_name, s_path)
            
            confirm = messagebox.askyesno("Profile Sync", "This script will sync your saves and deploy MO2 configuration.\nA backup will be created in the Standalone folder.\n\nContinue?")
            
            if confirm:
                sync.backup_original_windows_data()
                sync.deploy_mo2_profile()
                print("\n[FINISH] Your Standalone build is ready to play!")
                print("Please run the game via the Standalone folder.")

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
