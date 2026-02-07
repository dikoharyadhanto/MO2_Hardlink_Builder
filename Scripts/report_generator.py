import json
import sys
from pathlib import Path
from datetime import datetime

class ReportGenerator:
    def __init__(self, manifest_path=None, report_path=None, output_html=None):
        # Determine Base Path (EXE vs Script)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        # Default paths relative to the 'output' folder
        output_dir = base_path / "output"
        
        self.manifest_path = Path(manifest_path) if manifest_path else output_dir / "mapping_manifest.json"
        self.report_path = Path(report_path) if report_path else output_dir / "execution_report.json"
        self.output_html = Path(output_html) if output_html else output_dir / "report_builder.html"

    def generate(self, verification_results=None, show_deployment=True):
        execution = {}
        if show_deployment and self.report_path.exists():
            print(f">>> Reading execution report ({self.report_path.stat().st_size / 1024 / 1024:.2f} MB)...")
            with open(self.report_path, 'r') as f:
                execution = json.load(f)
        elif not verification_results:
            print(f"[!] Report generation skipped: No report file found and no verification results provided.")
            return

        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        # Calculate statistics
        total = len(execution)
        success_list = []
        failed_list = []
        
        hardlinks = 0
        copies = 0
        
        print(">>> Processing statistics...")
        for target, data in execution.items():
            status = data.get('status', 'N/A')
            method = data.get('method', 'N/A')
            
            if "SUCCESS" in status:
                success_list.append((target, data))
                if method == 'hardlink': hardlinks += 1
                elif method == 'copy': copies += 1
            else:
                failed_list.append((target, data))

        total_success = len(success_list)
        total_failed = len(failed_list)

        # Optimization: Data Limiting
        MAX_ROWS = 5000
        is_truncated = False
        display_list = failed_list.copy()
        
        if len(display_list) < MAX_ROWS:
            remaining = MAX_ROWS - len(display_list)
            display_list.extend(success_list[:remaining])
            if len(success_list) > remaining:
                is_truncated = True
        else:
            is_truncated = True

        print(f">>> Building HTML with {len(display_list)} rows (Total: {total})...")

        html_chunks = []
        html_chunks.append(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MO2 Hardlink Builder Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #e0e0e0; margin: 20px; }}
        .container {{ max-width: 1200px; margin: auto; }}
        .header {{ background: #2d2d2d; padding: 20px; border-radius: 8px; border-left: 5px solid #4CAF50; margin-bottom: 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #2d2d2d; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .stat-card h3 {{ margin: 0; font-size: 14px; color: #888; }}
        .stat-card p {{ margin: 10px 0 0; font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .warning-box {{ background: #443300; padding: 15px; border-radius: 8px; border-left: 5px solid #ff9800; margin-bottom: 20px; font-size: 14px; }}
        .error-box {{ background: #441111; padding: 15px; border-radius: 8px; border-left: 5px solid #ff3333; margin-bottom: 20px; font-size: 14px; }}
        .success-box {{ background: #114411; padding: 15px; border-radius: 8px; border-left: 5px solid #4CAF50; margin-bottom: 20px; font-size: 14px; }}
        
        .filter-bar {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
        .filter-btn {{ background: #3d3d3d; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; transition: background 0.2s; }}
        .filter-btn:hover {{ background: #555; }}
        .filter-btn.active {{ background: #4CAF50; }}

        table {{ width: 100%; border-collapse: collapse; background: #2d2d2d; border-radius: 8px; overflow: hidden; table-layout: fixed; }}
        th {{ background: #3d3d3d; color: #fff; text-align: left; padding: 12px; font-size: 14px; }}
        td {{ padding: 10px; border-bottom: 1px solid #3d3d3d; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        tr:hover {{ background: #353535; }}
        .status-success {{ color: #4CAF50; font-weight: bold; }}
        .status-failed {{ color: #f44336; font-weight: bold; }}
        .method-tag {{ background: #444; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
        .search-box {{ width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #444; background: #2d2d2d; color: #fff; box-sizing: border-box; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MO2 Hardlink Builder Report</h1>
            <p>Generated at: {now}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><h3>Total Files</h3><p>{total}</p></div>
            <div class="stat-card"><h3>Success</h3><p>{total_success}</p></div>
            <div class="stat-card"><h3>Hardlinks</h3><p>{hardlinks}</p></div>
            <div class="stat-card"><h3>Copies</h3><p>{copies}</p></div>
        </div>
""")

        # --- VERIFICATION SECTION ---
        if verification_results:
            missing = verification_results.get("missing_files", [])
            zeros = verification_results.get("zero_byte_files", [])
            configs = verification_results.get("config_mismatch", [])
            saves = verification_results.get("save_issues", [])
            quarantined = verification_results.get("quarantined_items", [])
            has_historic = verification_results.get("has_historic_quarantine", False)
            
            has_issues = any([missing, zeros, configs, saves])
            
            if has_issues:
                html_chunks.append('<div class="error-box"><h3>⚠️ Post-Deployment Verification Warnings</h3><ul>')
                
                if configs:
                    html_chunks.append(f"<li><strong>Config Mismatch:</strong> {len(configs)} issue(s) detected with INIs / Plugins / Load Order.</li>")
                    for c in configs: html_chunks.append(f"<li>&nbsp;&nbsp;&bull; {c}</li>")
                
                if missing:
                    html_chunks.append(f"<li><strong>Missing Files:</strong> {len(missing)} files from manifest are missing in Standalone folder.</li>")
                    for m in missing[:5]: html_chunks.append(f"<li>&nbsp;&nbsp;&bull; {m['file']} ({m['mod']})</li>")
                    if len(missing) > 5: html_chunks.append(f"<li>&nbsp;&nbsp;&bull; ... and {len(missing)-5} more.</li>")
                
                if zeros:
                    html_chunks.append(f"<li><strong>Zero-Byte Files:</strong> {len(zeros)} files have 0 bytes size.</li>")
                
                if saves:
                     html_chunks.append(f"<li><strong>Save Sync Issue:</strong> {len(saves)} issue(s) with save files.</li>")

                html_chunks.append('</ul></div>')

            # --- NEW: QUARANTINE SECTION ---
            if quarantined or has_historic:
                html_chunks.append('<div class="warning-box" style="background: #1a3a5a; border-left: 5px solid #3498db;"><h3>ℹ️ Manual Action Required: Quarantined Saves</h3><ul>')
                
                if quarantined:
                    html_chunks.append('<li>The following files from **this build** were moved to quarantine due to a conflict:</li>')
                    for q in quarantined:
                        html_chunks.append(f"<li>&nbsp;&nbsp;&bull; <strong>{q['file']}</strong><br>&nbsp;&nbsp;&nbsp;&nbsp;<small>Location: {q['location']}</small><br>&nbsp;&nbsp;&nbsp;&nbsp;<small>Reason: {q['reason']}</small></li>")
                
                if has_historic:
                    html_chunks.append('<li style="margin-top: 15px; color: #ffeb3b;"><strong>ℹ️ Notice:</strong> You have previous save backups in your quarantine history that haven\'t been resolved yet.</li>')
                    html_chunks.append('<li style="color: #ffc107;"><strong>⚠️ Warning:</strong> To prevent clutter, a limit of <strong>5 backups</strong> is enforced per location. When this limit is reached, the oldest backup will be <strong>automatically and permanently deleted</strong> during future builds.</li>')
                
                html_chunks.append('</ul></div>')

            if not has_issues and not quarantined and not has_historic:
                 html_chunks.append('<div class="success-box"><strong>✅ Verification Passed:</strong> All manifest files present, configs synced, and saves verified.</div>')

        if is_truncated:
            html_chunks.append(f"""
        <div class="warning-box">
            <strong>Portability Note:</strong> This report only shows failures and a subset of successful files (first {MAX_ROWS} rows) to maintain browser performance. 
            There are {total_success} successful files that are not shown individually.
        </div>
""")

        if show_deployment:
            html_chunks.append("""
            <input type="text" id="searchInput" class="search-box" placeholder="Search by file name or mod...">
            
            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterTable('all', this)">All</button>
                <button class="filter-btn" onclick="filterTable('FAILED', this)">Failures</button>
                <button class="filter-btn" onclick="filterTable('hardlink', this)">Hardlinks</button>
                <button class="filter-btn" onclick="filterTable('copy', this)">Copies</button>
            </div>
            
            <table id="reportTable">
                <thead>
                    <tr>
                        <th style="width: 50%;">Target File</th>
                        <th style="width: 25%;">Source Mod</th>
                        <th style="width: 15%;">Status</th>
                        <th style="width: 10%;">Method</th>
                    </tr>
                </thead>
                <tbody>
    """)

            for target, data in display_list:
                mod_origin = data.get('mod', 'Unknown')
                status = data.get('status', 'N/A')
                method = data.get('method', 'N/A')
                status_class = "status-success" if "SUCCESS" in status else "status-failed"
                
                html_chunks.append(f"""
                    <tr data-status="{status}" data-method="{method}">
                        <td title="{target}">{target}</td>
                        <td title="{mod_origin}">{mod_origin}</td>
                        <td class="{status_class}">{status}</td>
                        <td><span class="method-tag">{method}</span></td>
                    </tr>
    """)

            html_chunks.append("""
                </tbody>
            </table>
        </div>
    """)
        else:
            html_chunks.append('</div>')
        html_chunks.append("""
    <script>
        let currentFilter = 'all';

        function filterTable(filter, btn) {
            currentFilter = filter;
            
            // Update UI buttons
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            applyAllFilters();
        }

        document.getElementById('searchInput').addEventListener('keyup', function() {
            applyAllFilters();
        });

        function applyAllFilters() {
            let search = document.getElementById('searchInput').value.toLowerCase();
            let rows = document.querySelectorAll('#reportTable tbody tr');
            
            rows.forEach(row => {
                let status = row.getAttribute('data-status');
                let method = row.getAttribute('data-method');
                let text = row.textContent.toLowerCase();
                
                let matchesSearch = text.includes(search);
                let matchesFilter = true;
                
                if (currentFilter === 'FAILED') {
                    matchesFilter = status.includes('FAILED');
                } else if (currentFilter === 'hardlink' || currentFilter === 'copy') {
                    matchesFilter = (method === currentFilter);
                }
                
                row.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
""")

        with open(self.output_html, 'w', encoding='utf-8') as f:
            f.write("".join(html_chunks))
        print(f"[SUCCESS] Interactive report generated at: {self.output_html}")

