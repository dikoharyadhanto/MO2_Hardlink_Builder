import os
import sys
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from tqdm import tqdm

class ScannerEngine:
    def __init__(self, mo2_path, profile_name):
        self.mo2_path = Path(mo2_path)
        self.mods_dir = self.mo2_path / "mods"
        self.overwrite_dir = self.mo2_path / "overwrite" # MO2 Overwrite Folder
        self.profile_path = self.mo2_path / "profiles" / profile_name
        self.modlist_txt = self.profile_path / "modlist.txt"
        
        # Determine Base Path (EXE vs Script)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        # Output directory
        self.output_dir = base_path / "output"
        self.output_dir.mkdir(exist_ok=True)
        self.output_manifest = self.output_dir / "mapping_manifest.json"
        
        self.blacklist_files = [
            'meta.ini', 'mo2_separator.txt', 'thumbs.db', 'desktop.ini',
            'readme.txt', 'credits.txt', 'changelog.txt', 'license.txt',
            'readme.md', 'credits.md', 'changelog.md'
        ]
        self.blacklist_dirs = [
            '.hidden', 'fomod', 'readmes', 'readme', 'docs', 'documents', 
            'credits', 'changelog', 'licenses'
        ]
        self.blacklist_extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt']

    def _get_active_mods(self):
        if not self.modlist_txt.exists():
            raise FileNotFoundError(f"ERROR: modlist.txt not found at: {self.modlist_txt}")

        active_mods = []
        with open(self.modlist_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('+'):
                    active_mods.append(line[1:])
        return active_mods

    def _scan_folder(self, folder_path, mod_name, mapping_table):
        """Fungsi pembantu untuk memindai folder dan mengisi mapping_table."""
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d.lower() not in self.blacklist_dirs]

            for file_name in files:
                ext = Path(file_name).suffix.lower()
                if file_name.lower() in self.blacklist_files or ext in self.blacklist_extensions:
                    continue

                full_source = Path(root) / file_name
                rel_path = full_source.relative_to(folder_path)
                parts = rel_path.parts
                
                if parts[0].lower() == 'root':
                    target_path = Path(*parts[1:])
                    is_root = True
                elif parts[0].lower() == 'data':
                    target_path = rel_path
                    is_root = False
                else:
                    target_path = Path("Data") / rel_path
                    is_root = False
                
                target_key = str(target_path).replace("\\", "/")
                
                # Menimpa entri sebelumnya jika file sama ditemukan
                mapping_table[target_key] = {
                    "source": str(full_source).replace("\\", "/"),
                    "mod_origin": mod_name,
                    "is_root": is_root,
                    "size_bytes": full_source.stat().st_size
                }

    def build_mapping(self):
        active_mods = self._get_active_mods()
        mapping_table = {}
        
        print(f"\n[*] Processing Profile: {self.profile_path.name}")
        
        # 1. Scan Mods from Modlist (Priority Order)
        print(f"[*] Scanning {len(active_mods)} mods...")
        for mod_name in tqdm(active_mods, desc="Scanning Mods"):
            mod_folder = self.mods_dir / mod_name
            if mod_folder.exists():
                self._scan_folder(mod_folder, mod_name, mapping_table)

        # 2. Scan Overwrite Folder (Highest / Last Priority)
        if self.overwrite_dir.exists():
            print(f"[*] Including 'overwrite' folder as highest priority...")
            self._scan_folder(self.overwrite_dir, "MO2_Overwrite", mapping_table)

        with open(self.output_manifest, 'w', encoding='utf-8') as f:
            json.dump(mapping_table, f, indent=4)
        
        print(f"\n[SUCCESS]")
        print(f"Total unique files: {len(mapping_table)}")
        print(f"Manifest saved at: {os.path.abspath(self.output_manifest)}")


def get_path_interactively():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    print("[*] Please select your MO2 INSTALLATION FOLDER...")
    folder_selected = filedialog.askdirectory(title="Select Mod Organizer 2 Folder")
    root.destroy()
    return folder_selected

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        mo2_path, profile_name = sys.argv[1], sys.argv[2]
        scanner = ScannerEngine(mo2_path, profile_name)
        scanner.build_mapping()
    else:
        # UI for manual execution
        try:
            mo2_path = get_path_interactively()
            if not mo2_path:
                print("[!] Folder not selected. Script aborted.")
                exit()

            print(f"[*] Selected Folder: {mo2_path}")
            profile_name = input("[?] MO2 Profile Name (leave empty for 'Default'): ").strip()
            if not profile_name:
                profile_name = "Default"

            scanner = ScannerEngine(mo2_path, profile_name)
            scanner.build_mapping()
            
        except Exception as e:
            print(f"\n[CRITICAL ERROR] {str(e)}")
