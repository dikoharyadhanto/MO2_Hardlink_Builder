import os
import sys
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from tqdm import tqdm

class LinkerExecutor:
    def __init__(self, standalone_path, original_game_path):
        self.standalone_path = Path(standalone_path)
        self.game_path = Path(original_game_path)
        
        # Determine Base Path (EXE vs Script)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        # Manifest and Report are in 'output' folder
        self.output_dir = base_path / "output"
        self.manifest_file = self.output_dir / "mapping_manifest.json"
        self.report_file = self.output_dir / "execution_report.json"

    def _recursive_vanilla_deploy(self, src_root, dst_root, mode='copy'):
        """Internal recursive function to copy or link vanilla files with interactive fallback."""
        for item in src_root.iterdir():
            if item.name.lower() == '_commonredist': 
                continue
                
            target = dst_root / item.name
            
            if item.is_dir():
                target.mkdir(exist_ok=True)
                self._recursive_vanilla_deploy(item, target, mode)
            else:
                if not target.exists():
                    if mode == 'link':
                        try:
                            os.link(item, target) # Create Hardlink
                        except OSError as e:
                            # Interaction: If hardlink fails due to technical reasons
                            print(f"\n[!] HARDLINK FAILED: {item.name}")
                            
                            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                            choice = messagebox.askyesnocancel("Hardlink Failure", 
                                f"Failed to create hardlink for: {item.name}\n\n"
                                f"Error: {e}\n\n"
                                "Would you like to continue with COPY mode (File duplication)?\n"
                                "- Yes: Continue with Copy (Fallback)\n"
                                "- No: Skip this file\n"
                                "- Cancel: Abort entire process")
                            root.destroy()

                            if choice is True: # User chose Copy
                                shutil.copy2(item, target)
                            elif choice is None: # User chose Cancel
                                print("[!] Process forcefully aborted by user.")
                                os._exit(1)
                            else: # User chose No
                                continue
                    else:
                        shutil.copy2(item, target)

    def initial_vanilla_clone(self, mode='copy'):
        """Clones or links the root game folder from the original path to Standalone."""
        print(f"\n[*] STARTING FULL VANILLA CLONING (Mode: {mode.upper()})...")
        try:
            self._recursive_vanilla_deploy(self.game_path, self.standalone_path, mode)
            print("[SUCCESS] Vanilla Cloning finished with all core game libraries.")
        except Exception as e:
            print(f"[ERROR] Cloning failed: {e}")

    def clean_orphaned_files(self, dry_run=False):
        """Deletes files in standalone that are not in the manifest and are not core vanilla files."""
        if not self.manifest_file.exists():
            print("[!] Skip Cleaning: manifest not found.")
            return

        with open(self.manifest_file, 'r') as f:
            manifest = json.load(f)
        
        manifest_targets = {k.lower().replace("\\", "/") for k in manifest.keys()}
        
        # List of folders/files that MUST NOT be deleted (Vanilla Core / Engine)
        # Note: Broadened to capture standard Bethesda master files
        protected_prefixes = ['data/skyrim', 'data/fallout', 'data/starfield', 'data/oblivion', 'data/update']
        protected_extensions = ['.exe', '.dll', '.bsa', '.esm', '.ba2'] 
        
        print(f"[*] Cleaning up orphan files in: {self.standalone_path}")
        deleted_count = 0

        for root, dirs, files in os.walk(self.standalone_path):
            for file_name in files:
                full_path = Path(root) / file_name

                rel_path = full_path.relative_to(self.standalone_path)
                rel_key = str(rel_path).lower().replace("\\", "/")

                is_protected = False
                if any(rel_key.startswith(p) for p in protected_prefixes): is_protected = True
                if rel_key.count('/') == 0 and any(rel_key.endswith(ext) for ext in protected_extensions): is_protected = True
                if rel_key.endswith('.bsa'): is_protected = True
                
                if rel_key not in manifest_targets and not is_protected:
                    if not dry_run:
                        try:
                            os.remove(full_path)
                            print(f"[-] Deleted orphan: {rel_key}")
                            deleted_count += 1
                        except Exception as e:
                            print(f"[!] Failed to delete {rel_key}: {e}")
                    else:
                        print(f"[DRY RUN] Would delete: {rel_key}")
                        deleted_count += 1

        print(f"[SUCCESS] Cleaning finished. Total files deleted: {deleted_count}")

    def execute_mapping(self, clean=False):
        """Reads JSON and overwrites files in Standalone with mod files."""
        if clean:
            self.clean_orphaned_files()

        if not self.manifest_file.exists():
            print(f"[!] Error: {self.manifest_file.name} not found!")
            return

        with open(self.manifest_file, 'r') as f:
            manifest = json.load(f)

        print(f"[*] Starting Mod Deployment to: {self.standalone_path}")
        report = {}

        for target_rel_path, info in tqdm(manifest.items(), desc="Deploying Mods", unit="file", smoothing=0.1, miniters=1, dynamic_ncols=True, leave=False, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]"):
            source_path = Path(info['source'])
            target_full_path = self.standalone_path / target_rel_path
            
            try:
                # 1. OVERWRITE LOGIC: Remove old file to replace with new link/copy
                if target_full_path.exists():
                    if target_full_path.is_file() or target_full_path.is_symlink():
                        os.remove(target_full_path)
                    elif target_full_path.is_dir():
                        shutil.rmtree(target_full_path)

                # 2. Ensure Target Directory Exists
                if not target_full_path.parent.exists():
                    target_full_path.parent.mkdir(parents=True, exist_ok=True)

                # 3. Execution (Hardlink if same drive, Copy if different)
                source_drive = source_path.anchor.lower()
                target_drive = self.standalone_path.anchor.lower()
                
                if source_drive == target_drive:
                    os.link(source_path, target_full_path)
                    method = "hardlink"
                else:
                    shutil.copy2(source_path, target_full_path)
                    method = "copy"

                report[target_rel_path] = {"status": "SUCCESS", "method": method, "mod": info['mod_origin']}

            except Exception as e:
                print(f"[!] Failed to process {target_rel_path}: {str(e)}")
                report[target_rel_path] = {"status": "FAILED", "error": str(e), "mod": info['mod_origin']}

        with open(self.report_file, 'w') as f:
            json.dump(report, f, indent=4)
        
        print(f"\n[SUCCESS] Deployment complete.")
        print(f"Execution details can be viewed at: {self.report_file}")

def get_folder(title):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 3:
        standalone_p, steam_p, mode_p = sys.argv[1], sys.argv[2], sys.argv[3]
        clean_flag = "--clean" in sys.argv
        
        executor = LinkerExecutor(standalone_p, steam_p)
        
        if "--clone" in sys.argv:
            executor.initial_vanilla_clone(mode=mode_p)
            
        executor.execute_mapping(clean=clean_flag)
    else:
        # UI for manual execution
        try:
            print("[*] Select your ORIGINAL Game folder...")
            game_p = get_folder("Select Original Game Folder")
            if not game_p: exit()

            while True:
                print("[*] Select the DESTINATION folder for Standalone Build...")
                standalone_p = get_folder("Select Standalone Destination Folder")
                if not standalone_p: exit()

                if str(game_p).lower() in str(standalone_p).lower():
                    messagebox.showerror("Location Error", "Standalone folder cannot be inside the Original Game folder!")
                else:
                    break

            executor = LinkerExecutor(standalone_p, game_p)
            
            do_clone = messagebox.askyesno("Clone Vanilla", "Would you like to clone Vanilla files now?")
            if do_clone:
                mode = "link" if messagebox.askyesno("Mode", "Use Hardlinks for Vanilla?") else "copy"
                executor.initial_vanilla_clone(mode=mode)
            
            executor.execute_mapping()
            
        except Exception as e:
            print(f"\n[CRITICAL ERROR] {str(e)}")
