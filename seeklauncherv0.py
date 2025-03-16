import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import minecraft_launcher_lib
import subprocess
import os
import requests
import webbrowser
from threading import Thread
import sys

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("PyLauncher")
        self.root.geometry("800x600")
        
        # Configuration
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.settings = {
            "java_path": "",
            "ram": "4096",
            "resolution": "1280x720",
            "server_ip": ""
        }
        
        # Variables
        self.versions = []
        self.selected_version = tk.StringVar()
        self.username = tk.StringVar(value="Player")
        self.auth_method = tk.StringVar(value="offline")
        self.download_progress = tk.DoubleVar()
        
        # UI Setup
        self.create_notebook()
        self.load_settings()
        
    def create_notebook(self):
        # Create tabs
        self.notebook = ttk.Notebook(self.root)
        
        # Play Tab
        self.play_frame = ttk.Frame(self.notebook)
        self.create_play_tab()
        
        # Installations Tab
        self.install_frame = ttk.Frame(self.notebook)
        self.create_install_tab()
        
        # Skins Tab
        self.skin_frame = ttk.Frame(self.notebook)
        self.create_skin_tab()
        
        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.create_settings_tab()
        
        self.notebook.add(self.play_frame, text="Play")
        self.notebook.add(self.install_frame, text="Installations")
        self.notebook.add(self.skin_frame, text="Skins")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.pack(expand=True, fill="both")

    def create_play_tab(self):
        # Version Selection
        ttk.Label(self.play_frame, text="Version:").grid(row=0, column=0, padx=5, pady=5)
        self.version_combobox = ttk.Combobox(self.play_frame, textvariable=self.selected_version, state="readonly")
        self.version_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Username
        ttk.Label(self.play_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(self.play_frame, textvariable=self.username).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Server IP
        ttk.Label(self.play_frame, text="Server IP:").grid(row=2, column=0, padx=5, pady=5)
        self.server_entry = ttk.Entry(self.play_frame)
        self.server_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # Launch Button
        ttk.Button(self.play_frame, text="Launch Minecraft", command=self.launch_minecraft).grid(
            row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
        
        # Console Output
        self.console = tk.Text(self.play_frame, height=10, state="disabled")
        self.console.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        self.play_frame.grid_rowconfigure(4, weight=1)
        self.play_frame.grid_columnconfigure(1, weight=1)

    def create_install_tab(self):
        # Version List
        self.version_tree = ttk.Treeview(self.install_frame, columns=("type", "release"), show="headings")
        self.version_tree.heading("#0", text="Version")
        self.version_tree.heading("type", text="Type")
        self.version_tree.heading("release", text="Release Date")
        
        # Modloader Selection
        self.modloader_var = tk.StringVar()
        ttk.Combobox(self.install_frame, textvariable=self.modloader_var, 
                    values=["Vanilla", "Forge", "Fabric", "OptiFine"]).grid(row=0, column=1, padx=5, pady=5)
        
        # Install Button
        ttk.Button(self.install_frame, text="Install Version", command=self.install_version).grid(
            row=0, column=2, padx=5, pady=5)
        
        # Layout
        self.version_tree.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.install_frame.grid_rowconfigure(1, weight=1)
        self.install_frame.grid_columnconfigure(0, weight=1)
        
        # Load versions
        Thread(target=self.load_online_versions).start()

    def create_skin_tab(self):
        ttk.Label(self.skin_frame, text="Current Skin:").grid(row=0, column=0)
        self.skin_canvas = tk.Canvas(self.skin_frame, width=64, height=64)
        self.skin_canvas.grid(row=0, column=1)
        ttk.Button(self.skin_frame, text="Upload Skin", command=self.upload_skin).grid(row=1, column=0, columnspan=2)

    def create_settings_tab(self):
        # Java Path
        ttk.Label(self.settings_frame, text="Java Path:").grid(row=0, column=0)
        ttk.Entry(self.settings_frame, textvariable=self.settings["java_path"]).grid(row=0, column=1)
        ttk.Button(self.settings_frame, text="Browse", command=self.browse_java).grid(row=0, column=2)
        
        # RAM Allocation
        ttk.Label(self.settings_frame, text="RAM (MB):").grid(row=1, column=0)
        ttk.Spinbox(self.settings_frame, from_=1024, to=16384, textvariable=self.settings["ram"]).grid(row=1, column=1)
        
        # Resolution
        ttk.Label(self.settings_frame, text="Resolution:").grid(row=2, column=0)
        ttk.Entry(self.settings_frame, textvariable=self.settings["resolution"]).grid(row=2, column=1)
        
        # Save Button
        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings).grid(row=3, column=0, columnspan=2)

    def load_online_versions(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            for version in versions:
                if version["type"] == "release":
                    self.version_tree.insert("", "end", text=version["id"], 
                                          values=(version["type"], version["releaseTime"]))
        except Exception as e:
            self.log(f"Error loading versions: {str(e)}")

    def install_version(self):
        version = self.version_tree.item(self.version_tree.selection()[0])["text"]
        modloader = self.modloader_var.get()
        
        def install_thread():
            try:
                if modloader == "Forge":
                    minecraft_launcher_lib.forge.install_forge_version(version, self.minecraft_dir)
                elif modloader == "Fabric":
                    minecraft_launcher_lib.fabric.install_fabric(version, self.minecraft_dir)
                else:
                    minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                self.log(f"Successfully installed {version}")
            except Exception as e:
                self.log(f"Installation error: {str(e)}")
        
        Thread(target=install_thread).start()

    def launch_minecraft(self):
        version = self.selected_version.get()
        options = {
            "username": self.username.get(),
            "jvmArguments": [
                f"-Xmx{self.settings['ram']}M",
                f"-Xms{self.settings['ram']//2}M",
                f"-Dminecraft.resolution={self.settings['resolution']}"
            ],
            "server": self.server_entry.get()
        }
        
        if self.settings["java_path"]:
            options["executablePath"] = self.settings["java_path"]
        
        try:
            command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
            subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log("Launching Minecraft...")
        except Exception as e:
            self.log(f"Launch error: {str(e)}")

    def upload_skin(self):
        file_path = filedialog.askopenfilename(filetypes=[("Skin Files", "*.png")])
        if file_path:
            # Implement skin upload logic
            self.log("Skin uploaded successfully")

    def browse_java(self):
        path = filedialog.askopenfilename(title="Select Java Executable")
        if path:
            self.settings["java_path"] = path

    def save_settings(self):
        # Implement settings save to file
        self.log("Settings saved")

    def log(self, message):
        self.console.config(state="normal")
        self.console.insert("end", message + "\n")
        self.console.config(state="disabled")
        self.console.see("end")

    def load_settings(self):
        # Implement settings load from file
        pass

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()
