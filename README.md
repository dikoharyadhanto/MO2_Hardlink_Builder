# MO2 Hardlink Builder

### **Why I Created This Tool**
The primary reason I created this tool was a simple desire: to run Skyrim directly without the "middleman" that is MO2.

Mod Organizer 2 is an incredibly powerful tool for managing thousands of installed mods through its flexible Virtual File System (VFS). However, in my experience, a problem arises when thousands of mods are attempted to run at once; the VFS overhead adds significant game startup time—from the initial launch to the main menu—compared to running the game directly from its own folder.

Even though MO2 supports desktop shortcuts, I personally feel that launching Skyrim through MO2 creates the impression that the mods are only installed through a proxy. This tool was originally planned for my personal needs and my own experience playing Skyrim with a modlist that has grown to nearly 3500+ mods. I decided to publish it for the community members who share my perspective: Skyrim lovers who want to maximize their gameplay experience without being hindered by long loading times. This tool does not guarantee that your game will load instantly, as that depends on the weight of your modlist, but it will at least prune the startup loading times so your waiting time is reduced.

This tool does not attempt to reduce the advantages of MO2, which keeps your game folder pure and clean. In fact, I designed this tool to respect that very principle. The solution offered here is to perform a hardlink from your game folder and your MO2 mod directory to a standalone location that is isolated from your original files.

By using a hardlink system between the original game files and the MO2 mod list, this tool results in virtually zero additional disk space usage. Consequently, you can use this tool to create multiple standalone versions of your game, each with different mod lists from different MO2 profiles, without exhausting your storage capacity.

I am sharing the source code so that other modders can develop it further. I am not an experienced modder—in fact, this is my first modding tool. I am simply an ordinary user who loves Skyrim and wants to share what I have built for our collective convenience.

---

### **Key Features**

#### **1. High-Speed Hardlink Deployment**
* **NTFS Hardlink System:** Uses hardlink technology to generate standalone game folders. Windows recognizes them as real physical files, but they occupy **zero additional disk space** since they point directly to your existing MO2 data.
* **Rapid Build Time:** Deployment for 3500+ mods is completed in **3-5 minutes**. Conflict resolution is handled entirely in RAM before the writing process starts.
* **Native Engine Performance:** Eliminates VFS overhead during runtime, resulting in faster initial loading and better engine stability.

#### **2. Full Environment Hijacking & Isolation**
* **Local Profile Injection:** Uses a wrapper script to fully isolate the game environment. The game is forced to use a local `_profile` folder within the standalone directory for all data storage.
* **Isolated AppData & Documents:** `AppData/Local` and `Documents/My Games` paths are redirected. Your `.ini` settings, loadorder, and logs stay inside the standalone folder and never touch your Windows system folders.
* **Portable Save System:** Save games are automatically isolated within the standalone directory, preventing corruption between different modlists while allowing sync back to MO2 profiles.

#### **3. Identity-Based Safety Protocol**
* **Metadata Verification:** The tool uses a `standalone_metadata` folder to validate the target build folder.
* **Hard-Coded Security Lock:** Automatically blocks *Clean* or *Build* functions if an original `game.exe` or `steam.dll` is detected without the metadata identifier, preventing accidental wiping of your Steam/MO2 folders.

#### **4. Optimized Execution Workflow**
* **Pre-Resolved Manifest:** The Scanner reads MO2's `modlist.txt` and builds a final roadmap in memory. Overwritten files are never processed by the executor for maximum efficiency.
* **Atomic Cleanup:** The cleaner engine ensures the target folder is 100% cleared of leftover files before a new deployment begins.

#### **5. Data Audit & Reporting**
* **Interactive HTML Dashboard:** Generates a visual `report_builder.html` inside `standalone_metadata` after every build to track the origin of every file.
* **Technical JSON Logs:** Produces `mapping_manifest.json` and `execution_report.json` for deep technical auditing.

---

### **Limitations & Technical Constraints**

1.  **NTFS Requirement:** Only functions on **NTFS** drives. FAT32 or exFAT are not supported.
2.  **Single Drive Boundary:** For the **Zero-Space** feature, the Standalone folder must be on the same physical drive as MO2 and the Game. Otherwise, it defaults to **Copy Mode**.
3.  **Modlist Snapshot:** This is a static snapshot. You must re-run the Deployment process if you change your modlist or load order in MO2.
4.  **MO2 Execution Lock:** Do **not** run this tool through the MO2 executables list while MO2's VFS is active. It must be run as a standalone application.
5.  **Partial Support for Other Games:** Tested and confirmed for **Skyrim Anniversary Edition**. While the code is universal, it is provided as-is for other titles. It is **safe to try** as it never modifies original files.
6.  **Metadata Safety:** Do not delete the `standalone_metadata` file/folder inside your standalone directory, or the tool will block further updates to prevent accidental data loss.

---

### **How to Use**

#### **1. Initial Configuration**
Provide the following paths on first launch:
* **MO2 Path:** Your Mod Organizer 2 installation folder.
* **MO2 Profile:** The specific profile you wish to deploy.
* **Original Game Path:** Your clean/original Steam game folder.
* **Standalone Path:** Where the isolated build will be created.

#### **2. Main Menu Operations**
* **Option 1: Full Build & Deploy:** Automates cleaning, save rescue, environment setup, and hardlink deployment.
* **Option 2: Cleaning Only (Safe Wipe):** Securely empties the standalone folder.
    * **Save Rescue:** Automatically detects save progress in `_profile` and exports it to MO2.
    * **Conflict Handling:** Prompts you to **Overwrite** or **Isolate** if a save conflict is detected in MO2.
* **Option 3: Manual Sync:** Manually sync saves/settings between the Standalone `_profile` and MO2.

#### **3. Verification & Launch**
* **Launch:** Run the game via `skse64_loader.exe` in the Standalone folder. The **Hijack Wrapper** will redirect all data to the local `_profile`.
* **Data Audit:** All build info (HTML/JSON) is stored in the **`standalone_metadata`** folder inside your standalone directory.

---

### **Deployment Scenarios**
* **Same NTFS Drive:** Hardlink Mode (**Zero Space Used**).
* **Different Drives:** Copy Mode (Full disk space used for duplicated files).

---

### **Troubleshooting**
* **Deployment Time:** ~3–5 minutes for 3500+ mods on an SSD.
* **Bug Reporting:** Verify if your game runs in MO2 first. Only report issues if the game works in MO2 but fails specifically in this Standalone mode.
