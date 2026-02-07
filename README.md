# MO2 Hardlink Builder

A high-performance deployment tool designed to create **standalone, portable, and isolated** game environments from your Mod Organizer 2 setup.

## 🚀 Overview

Launching Skyrim (or other Bethesda games) through Mod Organizer 2's Virtual File System (VFS) is convenient but can introduce significant overhead, especially with massive modlists (3000+ mods). **MO2 Hardlink Builder** bypasses this overhead by creating a "real" physical game directory where mods are hardlinked directly into the game's Data folder.

The result? **Original engine startup speeds** with **zero additional disk space usage**, while keeping your original game folder and MO2 installation pristine.

---

## ✨ Key Features

### 1. Zero-Space NTFS Hardlinking
- **Physical Integration:** mods appear as real files in the game folder, allowing the engine to load them natively without VFS middleware.
- **Disk Efficiency:** Uses NTFS hardlinks. A 200GB modlist takes **0 bytes** of additional space because the files point to your existing MO2 mod folder.
- **Blazing Fast Deployment:** Deploys 3500+ mods in **3-5 minutes**.

### 2. Environment Hijacking & Total Isolation
- **`_profile` Redirection:** The tool "hijacks" the game's environment, forcing it to use a local `_profile` folder inside the standalone directory for everything.
- **Portable Saves & INIs:** `AppData/Local` and `Documents/My Games` are redirected. Your settings and saves never touch your Windows system folders.
- **Multiple Builds:** Create multiple standalone versions (e.g., one for "LOD Testing", one for "Gameplay") without them ever conflicting.

### 3. Identity-Based Safety
- **Anti-Corruption Guard:** The tool refuses to "Clean" or "Build" in any folder containing `Steam.dll` or original game executables unless it finds our `standalone_metadata` marker.
- **Path Locking:** Prevents selecting your original Game or MO2 folders as the deployment destination.

### 4. Interactive Reporting
- **Build Dashboard:** Generates an interactive `build_report.html` tracking the origin and status of every single file.
- **Audit Logs:** Full JSON manifests for technical troubleshooting.

---

## 🛠 Prerequisites

1.  **NTFS Filesystem:** Hardlinks only work on NTFS drives.
2.  **Same Physical Drive:** For **Zero-Space** mode, your Standalone folder MUST be on the same drive as your MO2 mods and the Game installation. (If on different drives, it defaults to **Copy Mode**, which uses full disk space).
3.  **Standalone Run:** Run this tool as a normal application. Do **NOT** run it through MO2's executable list.

---

## 📖 Usage Guide

### Step 1: Initial Configuration
Upon launch, the tool will guide you through selecting four key paths:
1.  **MO2 Path:** Your main Mod Organizer 2 installation.
2.  **MO2 Profile:** The specific profile you want to turn into a standalone build.
3.  **Original Game Path:** Your clean Steam/GOG installation folder.
4.  **Standalone Destination:** A **new, empty folder** where your build will live.

### Step 2: Main Operations

#### Option 1: Full Build & Deploy
This is the "One-Click" solution. It will:
- Safely backup any existing saves in the destination.
- Wipe the destination folder (if pre-existing).
- Scan your MO2 modlist and resolve conflicts in RAM.
- Deploy hardlinks for the Game and Mods.
- Inject the **Hijack Wrapper** for total isolation.

#### Option 2: Clean & Restore
Use this to securely delete a standalone build.
- **Save Rescue:** Automatically detects saves in the build and offers to sync them back to your MO2 profile before deletion.
- **Safety Check:** Ensures it only wipes folders it "owns" (via metadata markers).

#### Option 3: Manual Save Sync
Manually export saves from your Standalone build to MO2, or import from MO2 to the Standalone build.

---

## 🚀 How to Launch Your Build

Once deployed, go to your Standalone folder. You will see:
- `How to Launch.txt`: Detailed instructions generated specifically for your build.
- `skse64_loader.exe` (or your game's loader).

**IMPORTANT:** Simply run the loader (e.g., `skse64_loader.exe`) as usual. 
- You may notice a hidden `_skse64_loader_original.exe`. **Ignore it.** 
- The visible `skse64_loader.exe` is actually our **Hijack Wrapper** which sets up the portable environment before triggering the real game.

---

<<<<<<< HEAD
## ⚠️ Safety & Constraints

- **Static Snapshot:** This is a physical copy of your modlist. If you change your load order or add mods in MO2, you must **Rebuild** (Option 1).
- **Metadata Protection:** Do not delete the `standalone_metadata` folder inside your build, or the tool will lose track of the folder's identity and block updates/cleaning for safety.
- **Game Support:** While optimized for **Skyrim SE/AE**, the tool supports most Bethesda titles (Fallout 4, Starfield, New Vegas, etc.).

---

## 🛠 Troubleshooting

- **Game Crashes?** Verify if the game runs through MO2 first. If it works in MO2 but not here, check the `build_report.html` for missing files.
- **Large Disk Usage?** Ensure your Standalone folder is on the same drive as your mods. If they are on different drives, Windows must copy the files instead of hardlinking.
=======
### **Troubleshooting**
* **Deployment Time:** ~3–5 minutes for 3500+ mods on an SSD.
* **Bug Reporting:** Verify if your game runs in MO2 first. Only report issues if the game works in MO2 but fails specifically in this Standalone mode.
>>>>>>> 37058d9c86ea37a9de8d3dc2ad16aba95646d27d
