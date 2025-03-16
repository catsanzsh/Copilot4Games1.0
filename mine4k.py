#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import minecraft_launcher_lib
import subprocess
import os
import json
import sys
import platform
from threading import Thread
from datetime import datetime

class MineSeek4KLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("MineSeek4K")
        self.root.geometry("800x600")
        
        # Configuration
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.config_path = os.path.join(self.minecraft_dir, "mineseek4k_config.json")
        self.default_settings = {
            "java_path": self.find_java(),
            "ram": 4096,
            "resolution": "1280x720",
            "server_ip": "",
            "last_username": "Player",
            "auth_method": "offline"
        }
        self.settings = self.default_settings.copy()
        
        # Create necessary directories
        os.makedirs(self.minecraft_dir, exist_ok=True)
        
        # Load settings
        self.load_settings()
        
        # UI Setup
        self.create_notebook()
        self.load_installed_versions()
        
        # Start version list loading
        Thread(target=self.load_online_versions, daemon=True).start()

    def find_java(self):
        try:
            return minecraft_launcher_lib.utils.get_java_executable()
        except Exception:
            return "java"  # Fallback to system PATH

    def create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        
        # Play Tab
        self.play_frame = ttk.Frame(self.notebook)
        self.create_play_tab()
        
        # Install Tab
        self.install_frame = ttk.Frame(self.notebook)
        self.create_install_tab()
        
        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.create_settings_tab()
        
        self.notebook.add(self.play_frame, text="Play")
        self.notebook.add(self.install_frame, text="Install")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.pack(expand=True, fill="both")

    def create_play_tab(self):
        ttk.Label(self.play_frame, text="Version:").grid(row=0, column=0, padx=5, pady=5)
        self.version_combobox = ttk.Combobox(self.play_frame, state="readonly")
        self.version_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(self.play_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(self.play_frame)
        self.username_entry.insert(0, self.settings["last_username"])
        self.username_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(self.play_frame, text="Server IP:").grid(row=2, column=0, padx=5, pady=5)
        self.server_entry = ttk.Entry(self.play_frame)
        self.server_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(self.play_frame, text="Launch Minecraft", command=self.launch_minecraft).grid(
            row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        
        self.console = tk.Text(self.play_frame, height=10, state="disabled")
        self.console.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        self.play_frame.grid_rowconfigure(4, weight=1)
        self.play_frame.grid_columnconfigure(1, weight=1)

    def create_install_tab(self):
        self.version_tree = ttk.Treeview(self.install_frame, columns=("type", "date"), show="headings")
        self.version_tree.heading("#0", text="Version")
        self.version_tree.heading("type", text="Type")
        self.version_tree.heading("date", text="Release Date")
        self.version_tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
        
        self.modloader_var = tk.StringVar(value="Vanilla")
        ttk.Combobox(self.install_frame, textvariable=self.modloader_var, 
                    values=["Vanilla", "Forge", "Fabric"], state="readonly").grid(row=1, column=0, padx=5)
        
        self.install_btn = ttk.Button(self.install_frame, text="Install", command=self.install_version)
        self.install_btn.grid(row=1, column=1, padx=5)
        
        self.progress = ttk.Progressbar(self.install_frame, mode="determinate")
        self.progress.grid(row=1, column=2, padx=5, sticky="ew")
        
        self.install_frame.grid_rowconfigure(0, weight=1)
        self.install_frame.grid_columnconfigure(0, weight=1)

    def create_settings_tab(self):
        ttk.Label(self.settings_frame, text="Java Path:").grid(row=0, column=0, sticky="w")
        self.java_entry = ttk.Entry(self.settings_frame)
        self.java_entry.insert(0, self.settings["java_path"])
        self.java_entry.grid(row=0, column=1, sticky="ew")
        ttk.Button(self.settings_frame, text="Browse", command=self.browse_java).grid(row=0, column=2)
        
        ttk.Label(self.settings_frame, text="RAM (MB):").grid(row=1, column=0, sticky="w")
        self.ram_spin = ttk.Spinbox(self.settings_frame, from_=1024, to=32768, increment=1024)
        self.ram_spin.set(self.settings["ram"])
        self.ram_spin.grid(row=1, column=1, sticky="ew")
        
        ttk.Label(self.settings_frame, text="Resolution:").grid(row=2, column=0, sticky="w")
        self.res_entry = ttk.Entry(self.settings_frame)
        self.res_entry.insert(0, self.settings["resolution"])
        self.res_entry.grid(row=2, column=1, sticky="ew")
        
        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings).grid(
            row=3, column=0, columnspan=3, pady=10)

    def load_installed_versions(self):
        versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
        installed = [v["id"] for v in versions if v["type"] == "release"]
        self.version_combobox["values"] = installed
        if installed:
            self.version_combobox.current(0)

    def load_online_versions(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            for version in versions:
                if version["type"] == "release":
                    self.version_tree.insert("", "end", text=version["id"], 
                                          values=(version["type"], version["releaseTime"]))
        except Exception as e:
            self.log(f"Error loading versions: {e}")

    def install_version(self):
        selected = self.version_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a version first!")
            return
        
        version = self.version_tree.item(selected[0])["text"]
        modloader = self.modloader_var.get()
        
        def install_task():
            try:
                self.install_btn["state"] = "disabled"
                self.progress["value"] = 0
                
                def update_progress(current, total):
                    self.progress["value"] = (current / total) * 100
                    self.root.update_idletasks()
                
                if modloader == "Forge":
                    minecraft_launcher_lib.forge.install_forge_version(version, self.minecraft_dir, callback=update_progress)
                elif modloader == "Fabric":
                    minecraft_launcher_lib.fabric.install_fabric(version, self.minecraft_dir, callback=update_progress)
                else:
                    minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir, callback=update_progress)
                
                self.log(f"Successfully installed {version}")
                self.load_installed_versions()
                
            except Exception as e:
                self.log(f"Installation failed: {e}")
                messagebox.showerror("Install Error", str(e))
            finally:
                self.install_btn["state"] = "normal"
                self.progress["value"] = 0
        
        Thread(target=install_task, daemon=True).start()

    def launch_minecraft(self):
        version = self.version_combobox.get()
        username = self.username_entry.get()
        
        if not version:
            messagebox.showerror("Error", "Select a Minecraft version!")
            return
        if not username:
            messagebox.showerror("Error", "Enter a username!")
            return
        
        self.settings["last_username"] = username
        self.save_settings()
        
        options = {
            "username": username,
            "jvmArguments": [
                f"-Xmx{self.settings['ram']}M",
                f"-Xms{self.settings['ram']//2}M",
                f"-Dminecraft.resolution={self.settings['resolution']}"
            ],
            "server": self.server_entry.get(),
            "executablePath": self.settings["java_path"]
        }
        
        try:
            command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
            subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log(f"Launched Minecraft {version}")
        except Exception as e:
            self.log(f"Launch failed: {e}")
            messagebox.showerror("Launch Error", str(e))

    def browse_java(self):
        initial = self.settings["java_path"] or self.find_java()
        path = filedialog.askopenfilename(title="Select Java Executable", initialfile=initial)
        if path:
            self.java_entry.delete(0, "end")
            self.java_entry.insert(0, path)

    def save_settings(self):
        try:
            self.settings.update({
                "java_path": self.java_entry.get(),
                "ram": int(self.ram_spin.get()),
                "resolution": self.res_entry.get()
            })
            
            with open(self.config_path, "w") as f:
                json.dump(self.settings, f)
            
            self.log("Settings saved successfully")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")

    def load_settings(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                self.log(f"Error loading settings: {e}")

    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.console.config(state="normal")
        self.console.insert("end", timestamp + message + "\n")
        self.console.config(state="disabled")
        self.console.see("end")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        MineSeek4KLauncher(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Launcher crashed: {str(e)}")
        sys.exit(1)
