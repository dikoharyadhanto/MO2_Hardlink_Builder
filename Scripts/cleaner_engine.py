import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

class CleanerEngine:
    def __init__(self, sa_path, mo2_path, steam_path=None, docs_name="Skyrim Special Edition", appdata_name="Skyrim Special Edition", game_name="Skyrim SE", profile_name="Default", portable_mode=True):
        self.sa_path = Path(sa_path).resolve()
        self.mo2_path = Path(mo2_path).resolve()
        self.steam_path = Path(steam_path).resolve() if steam_path else None
        self.portable_mode = portable_mode
        
        # New Dynamic Backup Path in LocalAppData
        self.backup_root = Path(os.environ['LOCALAPPDATA']) / "MO2_Hardlink_Builder" / game_name / profile_name / "Backups"
        
        # Only ensure backup directory if NOT in portable mode (safety)
        if not self.portable_mode:
            self.backup_root.mkdir(parents=True, exist_ok=True)
        
        self.win_docs = Path(os.path.expanduser(f"~/Documents/My Games/{docs_name}"))
        self.win_appdata = Path(os.environ['LOCALAPPDATA']) / appdata_name

    def is_inside(self, child, parent):
        """Checks if a path is inside another path."""
        try:
            child_p = Path(child).resolve()
            parent_p = Path(parent).resolve()
            return parent_p in child_p.parents or child_p == parent_p
        except:
            return False

    def check_safety(self):
        """Checks for safety before proceeding."""
        # 1. Check if the target folder is the MO2 folder or its parent (or nested)
        if self.is_inside(self.sa_path, self.mo2_path):
            return False, "FORBIDDEN: Standalone folder cannot be INSIDE or IS the MO2 folder!"
        if self.is_inside(self.mo2_path, self.sa_path):
            return False, "FORBIDDEN: You cannot select a parent folder of MO2 as the Standalone destination!"
        
        # 2. Check if the target folder is the Steam installation folder (or nested/parent)
        if self.steam_path:
            if self.is_inside(self.sa_path, self.steam_path):
                return False, "FORBIDDEN: Standalone folder cannot be INSIDE or IS your Original Game folder!"
            if self.is_inside(self.steam_path, self.sa_path):
                return False, "FORBIDDEN: You cannot select a parent folder of your Game installation (like Steam root) as the Standalone destination!"

        # 3. Standalone Identity Check (Allows bypass for rebuilds)
        standalone_markers = ["standalone_metadata", "_profile", "_Profile_Backup"]
        is_standalone = any((self.sa_path / m).exists() for m in standalone_markers)

        # 4. Extra Protection: Check if it looks like a Steam folder
        if not is_standalone:
            steam_indicators = ["steam.exe", "Steam.dll", "steam_api64.dll"]
            if any((self.sa_path / indicator).exists() for indicator in steam_indicators):
                 return False, "FORBIDDEN FOLDER! This folder contains Steam system files. Cleaning is blocked for your safety."

        # 5. Check if the main script exists in the target folder
        main_scripts = ['standalone_build_deploy.py']
        for script in main_scripts:
            if (self.sa_path / script).exists():
                return False, f"SCRIPT FOLDER! You selected a folder containing '{script}'. Standalone must be in a separate directory."

        return True, "Safe"

    def restore_profiles(self):
        print("\n[*] Attempting to restore original Windows profiles...")
        
        # Restore Documents (Only INI files, keep Saves untouched)
        doc_backup = self.backup_root / "Documents"
        if doc_backup.exists():
            print("    -> Restoring original INI files...")
            for ini in doc_backup.iterdir():
                if ini.is_file():
                    dst = self.win_docs / ini.name
                    shutil.copy2(ini, dst)
                    print(f"       [Restored] {ini.name}")
            
        # Restore AppData
        app_backup = self.backup_root / "AppData"
        if app_backup.exists():
            if self.win_appdata.exists():
                shutil.rmtree(self.win_appdata)
            shutil.copytree(app_backup, self.win_appdata)
            print("[SUCCESS] Original AppData/Plugins data restored.")

        if not doc_backup.exists() and not app_backup.exists():
            print("[!] No backup found to restore. Skipping...")

    def total_cleanup(self):
        print(f"\n[*] CLEANING STANDALONE DIRECTORY: {self.sa_path}")
        
        # Absolute Wipe (Safety is now handled at path selection in main script)
        for item in self.sa_path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                print(f"  [Deleted] {item.name}")
            except Exception as e:
                print(f"  [Failed] {item.name}: {e}")
        
        print(f"\n[CLEAN] Standalone folder is now 100% clean (Absolute Fresh Start).")

def get_path_ui(title):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 7:
        # Full CLI usage from main script
        sa_p = sys.argv[1]
        mo2_p = sys.argv[2]
        game_p = sys.argv[3]
        docs_n = sys.argv[4]
        app_n = sys.argv[5] 
        g_name = sys.argv[6]
        p_name = sys.argv[7]

        cleaner = CleanerEngine(sa_p, mo2_p, game_p, docs_n, app_n, game_name=g_name, profile_name=p_name)
        is_safe, message = cleaner.check_safety()
        if is_safe:
            cleaner.restore_profiles()
            cleaner.total_cleanup()
        else:
            print(f"[ERROR] {message}")
    elif len(sys.argv) > 2:
        # Minimal CLI
        sa_p, mo2_p = sys.argv[1], sys.argv[2]
        cleaner = CleanerEngine(sa_p, mo2_p)
        is_safe, message = cleaner.check_safety()
        if is_safe:
            cleaner.restore_profiles()
            cleaner.total_cleanup()
        else:
            print(f"[ERROR] {message}")
    else:
        # UI for manual execution
        print("MO2 HARDLINK BUILDER: CLEANER & RESTORE ENGINE")
        print("---------------------------------------------")
        
        # 1. Select MO2 once as security reference
        mo2_p = ""
        while not mo2_p:
            mo2_p = get_path_ui("Select MO2 Folder (Security Reference)")
            if not mo2_p:
                print("[!] Selecting the MO2 folder is required for security.")

        # 2. Standalone Folder Validation Loop
        while True:
            sa_p = get_path_ui("Select Standalone Folder to CLEAN")
            if not sa_p:
                print("[!] Operation cancelled by user.")
                exit()

            cleaner = CleanerEngine(sa_p, mo2_p)
            is_safe, message = cleaner.check_safety()

            if is_safe:
                # Final confirmation
                if messagebox.askyesno("Final Confirmation", f"Standalone folder is valid.\n\nAre you sure you want to empty:\n{sa_p}?\nAll files inside will be deleted!"):
                    cleaner.restore_profiles()
                    cleaner.total_cleanup()
                    print("\n[FINISH] Standalone cleaned. MO2 remains untouched.")
                    break # Exit loop after completion
            else:
                # Show error and retry
                messagebox.showerror("CRITICAL SECURITY", message)
                print(f"[REJECTED] {message}")
