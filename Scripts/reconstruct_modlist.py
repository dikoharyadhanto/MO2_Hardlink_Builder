import os
import re
import html
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

class ModlistReconstructor:
    def __init__(self, html_path, mods_dir):
        self.html_path = Path(html_path).resolve()
        self.mods_dir = Path(mods_dir).resolve()
        self.output_file = Path("modlist.txt")
        # Daftar file internal yang tidak boleh dijadikan separator
        self.vanilla_masters = {
            "skyrim.esm", "update.esm", "dawnguard.esm", 
            "hearthfires.esm", "dragonborn.esm", "skyrim.exe"
        }

    def parse_html_priorities(self):
        print(f"[*] Mengekstrak data (mod & separator) dari HTML...")
        with open(self.html_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        current_priority = None
        current_name = None
        in_mod_row = False
        
        # Patterns
        priority_pattern = re.compile(r'<td[^>]*>\s*(\d+)\s*</td>', re.IGNORECASE)
        name_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
        summary_pattern = re.compile(r'<summary class="group-summary">(.*?)</summary>', re.IGNORECASE)
        
        for line in lines:
            # 1. Cek apakah ini Separator (Category)
            summary_match = summary_pattern.search(line)
            if summary_match:
                sep_name = html.unescape(summary_match.group(1)).strip()
                if sep_name:
                    entries.append({"type": "separator", "name": sep_name})
                continue

            # 2. Cek apakah ini awal row mod
            if '<tr' in line.lower():
                in_mod_row = True
                current_priority = None
                current_name = None
                continue
                
            if in_mod_row:
                # Priority
                if current_priority is None:
                    match = priority_pattern.search(line)
                    if match:
                        current_priority = int(match.group(1))
                        continue
                
                # Name
                if current_priority is not None and current_name is None:
                    match = name_pattern.search(line)
                    if match:
                        raw_name = match.group(1)
                        clean_name = re.sub(r'<[^>]+>', '', raw_name).strip()
                        clean_name = html.unescape(clean_name)
                        if clean_name:
                            current_name = clean_name
                        continue
                
                # Status-badge (confirming it's a mod)
                if current_priority is not None and current_name is not None:
                    if 'status-badge' in line:
                        entries.append({"type": "mod", "priority": current_priority, "name": current_name})
                        in_mod_row = False
                        continue
                
                # End of row
                if '</tr>' in line.lower():
                    in_mod_row = False
        
        print(f"[*] Ditemukan {len(entries)} entri (mod + separator) dari HTML")
        return entries

    def run(self):
        html_entries = self.parse_html_priorities()
        
        print(f"[*] Scanning folder fisik: {self.mods_dir}")
        physical_mods = {item.name for item in self.mods_dir.iterdir() if item.is_dir()}
        physical_mods_lower = {name.lower(): name for name in physical_mods}
        
        # List urutan dari Prioritas Rendah ke Tinggi (Urutan Tampilan GUI dari Atas ke Bawah)
        gui_order = []
        processed_names = set()

        # 1. Masukkan data dari HTML sesuai urutan aslinya
        for entry in html_entries:
            name = entry['name']
            
            if entry['type'] == 'separator':
                # Pastikan format separator: "Name_separator"
                sep_line = name if name.endswith("_separator") else f"{name}_separator"
                
                # Cek apakah folder separator ini ada di fisik (untuk menandainya sebagai processed)
                # MO2 terkadang menyimpan folder fisik untuk separator
                if sep_line in physical_mods:
                    processed_names.add(sep_line)
                elif name in physical_mods:
                    processed_names.add(name)
                
                gui_order.append(sep_line)
            
            elif entry['type'] == 'mod':
                lowered_name = name.lower()
                
                # Abaikan jika itu file Vanilla Masters (Biarkan MO2 yang kelola)
                if lowered_name in self.vanilla_masters:
                    continue

                if name in physical_mods:
                    gui_order.append(f"+{name}")
                    processed_names.add(name)
                elif lowered_name in physical_mods_lower:
                    # Case insensitive match jika case aslinya beda
                    actual_name = physical_mods_lower[lowered_name]
                    gui_order.append(f"+{actual_name}")
                    processed_names.add(actual_name)
                else:
                    # Mod di HTML tapi folder tidak ada -> tetap masukkan sebagai +Name (uninstalled/missing)
                    # Atau bisa juga ini sebenarnya separator yang masuk ke list mod (unlikely with status-badge filter)
                    gui_order.append(f"+{name}")

        # 2. Masukkan Mod Asing (Unknown) ke PRIORITAS TERTINGGI
        # Sesuai permintaan: Ditaruh paling bawah di GUI agar menimpa semuanya
        unknown_mods = sorted(list(physical_mods - processed_names))
        if unknown_mods:
            print(f"[*] Menambahkan {len(unknown_mods)} mod asing ke prioritas tertinggi.")
            gui_order.append("=== UNKNOWN MODS (OVERWRITE) ===_separator")
            for mod in unknown_mods:
                gui_order.append(f"+{mod}")

        # 3. Tulis ke File (MO2 Standard)
        # MO2 membaca file dari ATAS (High Priority) ke BAWAH (Low Priority)
        # Jadi kita harus MEMBALIK (Reverse) daftar gui_order kita.
        # GUI: [Prio 0, Prio 1, Prio 2] -> File: [Prio 2, Prio 1, Prio 0]
        
        file_content = list(reversed(gui_order))
        file_content.insert(0, "# This file was automatically generated by Resonator Final Fix")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(file_content))
            
        print("-" * 50)
        print(f"[SUCCESS] File '{self.output_file}' berhasil dibuat!")
        print(f"LOGIKA: Baris 1 di file adalah Prioritas TERTINGGI (Paling Bawah di GUI).")
        print(f"LOGIKA: Baris terakhir di file adalah Prioritas TERENDAH (Paling Atas di GUI).")
        print("-" * 50)

def get_path_ui(title):
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title)
    root.destroy(); return path

if __name__ == "__main__":
    html_p = Path("Nirn_Modlist_2026.html")
    if not html_p.exists():
        root = tk.Tk(); root.withdraw()
        html_p = filedialog.askopenfilename(title="Pilih Nirn_Modlist_2026.html")
        root.destroy()
    
    mods_p = get_path_ui("Pilih Folder 'mods' MO2")
    
    if html_p and mods_p:
        app = ModlistReconstructor(html_p, mods_p)
        app.run()
    
    input("\nTekan ENTER untuk keluar...")