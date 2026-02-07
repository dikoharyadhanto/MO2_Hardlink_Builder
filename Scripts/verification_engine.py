import os
import json
import filecmp
from pathlib import Path
from tqdm import tqdm

class VerificationEngine:
    def __init__(self):
        self.results = {
            "missing_files": [],
            "zero_byte_files": [],
            "config_mismatch": [],
            "save_issues": [],
            "quarantined_items": [],
            "has_historic_quarantine": False
        }

    def verify_deployment(self, manifest_path=None, standalone_path=None):
        """Checks if files in manifest exist in standalone path."""
        if not manifest_path or not Path(manifest_path).exists():
            return
            
        print("[*] Verifying Deployment Integrity...")
        manifest_p = Path(manifest_path)
        sa_p = Path(standalone_path)

        try:
            with open(manifest_p, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"[!] Error loading manifest: {e}")
            return

        total = len(manifest)
        
        # Using tqdm for progress bar
        for relative_path, info in tqdm(manifest.items(), desc="Verifying Files", unit="file", smoothing=0.1):
            target_path = sa_p / relative_path
            
            # Check for Hijacked original if not found as is
            exists = target_path.exists()
            if not exists and relative_path.lower().endswith(".exe"):
                # Potential hijacked file
                original_name = f"_{Path(relative_path).stem}_original.exe"
                alt_path = target_path.parent / original_name
                if alt_path.exists():
                    exists = True
                    target_path = alt_path # Use the original for size check
            
            if not exists:
                self.results["missing_files"].append({
                    "file": relative_path,
                    "mod": info.get('mod_origin', 'Unknown')
                })
            elif target_path.stat().st_size == 0 and info.get('size_bytes', 1) > 0:
                 self.results["zero_byte_files"].append({
                    "file": relative_path,
                    "mod": info.get('mod_origin', 'Unknown')
                })

    def verify_configs(self, mo2_profile_path, appdata_path, doc_path, ini_prefix="Skyrim"):
        """Compares plugins, loadorder, and INIs."""
        print("[*] Verifying Configuration Synchronization...")
        mo2_p = Path(mo2_profile_path)
        app_p = Path(appdata_path)
        doc_p = Path(doc_path)

        # 1. Text Configs (AppData)
        for filename in ["plugins.txt", "loadorder.txt"]:
            src = mo2_p / filename
            dst = app_p / filename
            self._compare_files(src, dst, filename, "Local AppData")

        # 2. INI Files (Documents)
        for ini in [f"{ini_prefix}.ini", f"{ini_prefix}Prefs.ini", f"{ini_prefix}Custom.ini"]:
            src = mo2_p / ini
            dst = doc_p / ini
            
            # Special handling for Custom.ini to ignore sLocalSavePath
            ignore_pattern = "sLocalSavePath" if "Custom" in ini else None
            self._compare_files(src, dst, ini, "Documents", ignore_line=ignore_pattern)

    def _compare_files(self, src, dst, label, location_name, ignore_line=None):
        """Helper to compare file contents."""
        if not src.exists():
            return
        
        if not dst.exists():
            self.results["config_mismatch"].append(f"{label} missing in {location_name}")
            return

        try:
            with open(src, 'r', errors='ignore', encoding='utf-8-sig') as f1, \
                 open(dst, 'r', errors='ignore', encoding='utf-8-sig') as f2:
                
                c1 = [l.strip().lower() for l in f1.readlines() if l.strip()]
                c2 = [l.strip().lower() for l in f2.readlines() if l.strip()]
                
                if ignore_line:
                    pattern = ignore_line.lower()
                    c1 = [l for l in c1 if pattern not in l]
                    c2 = [l for l in c2 if pattern not in l]

                if c1 != c2:
                    self.results["config_mismatch"].append(f"{label} differs from MO2")
        except Exception as e:
            self.results["config_mismatch"].append(f"Error reading {label}: {str(e)}")

    def verify_saves(self, mo2_profile_path, doc_save_path, run_timestamp=None):
        """Checks if all saves are synchronized, including timestamped quarantine folders."""
        print("[*] Verifying Save Games...")
        mo2_saves_dir = Path(mo2_profile_path) / "saves"
        doc_saves_dir = Path(doc_save_path) / "Saves"

        if not mo2_saves_dir.exists():
            return

        try:
            # 1. Map existing saves in destination (Root + All Quarantines)
            doc_saves = {f.name for f in doc_saves_dir.glob("*.[es][sk][se]*")}
            
            # Helper to process quarantine folders
            def process_q_dir(root, pattern, location_label, is_current=False):
                for q_dir in root.glob(pattern):
                    if q_dir.is_dir():
                        # If we have a run_timestamp, check if this is the "current" one
                        is_this_current = (run_timestamp and run_timestamp in q_dir.name)
                        
                        if not is_this_current:
                            self.results["has_historic_quarantine"] = True
                        
                        q_files = [f.name for f in q_dir.glob("*.[es][sk][se]*")]
                        for qf in q_files:
                            doc_saves.add(qf)
                            # Only report the "latest" (current run) in the detailed list
                            if is_this_current:
                                self.results["quarantined_items"].append({
                                    "file": qf,
                                    "location": str(q_dir),
                                    "reason": f"Newer/Conflicting save from {location_label} moved to current quarantine."
                                })

            process_q_dir(doc_saves_dir, "MO2_import_save*", "MO2")
            process_q_dir(mo2_saves_dir, "Standalone_Export_save*", "Standalone")

            # 2. Compare against MO2 Source
            mo2_saves = {f.name for f in mo2_saves_dir.glob("*.[es][sk][se]*")}
            
            missing = mo2_saves - doc_saves
            if missing:
                self.results["save_issues"].append(f"Missing {len(missing)} save files in Standalone folder.")
                for m in sorted(list(missing))[:5]:
                    print(f"    [-] Missing: {m}")
            
        except Exception as e:
            self.results["save_issues"].append(f"Error checking saves: {str(e)}")

    def run_all_checks(self, manifest_path=None, standalone_path=None, mo2_profile_path=None, appdata_path=None, doc_save_path=None, ini_prefix="Skyrim", run_timestamp=None):
        if manifest_path:
            self.verify_deployment(manifest_path, standalone_path)
            
        if mo2_profile_path and appdata_path and doc_save_path:
            self.verify_configs(mo2_profile_path, appdata_path, doc_path=doc_save_path, ini_prefix=ini_prefix)
            self.verify_saves(mo2_profile_path, doc_save_path, run_timestamp=run_timestamp)
            
        return self.results
