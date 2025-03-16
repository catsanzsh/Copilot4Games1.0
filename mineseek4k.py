import tkinter as tk
from tkinter import ttk
import minecraft_launcher_lib
import subprocess
import os

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Minecraft Launcher")
        
        # Minecraft directory
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        # Variables
        self.versions = []
        self.selected_version = tk.StringVar()
        self.username = tk.StringVar()
        
        # Setup UI
        self.setup_ui()
        
        # Load versions
        self.load_versions()

    def setup_ui(self):
        # Username
        ttk.Label(self.root, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.root, textvariable=self.username).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Version Select
        ttk.Label(self.root, text="Version:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.version_combobox = ttk.Combobox(self.root, textvariable=self.selected_version, state="readonly")
        self.version_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Launch Button
        self.launch_button = ttk.Button(self.root, text="Launch Minecraft", command=self.launch_minecraft)
        self.launch_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    def load_versions(self):
        # Get available versions and reverse order to show newest first
        self.versions = minecraft_launcher_lib.utils.get_available_versions(self.minecraft_dir)
        self.versions = [v["id"] for v in self.versions if v["type"] == "release"]
        self.versions.reverse()
        self.version_combobox["values"] = self.versions
        if self.versions:
            self.selected_version.set(self.versions[0])

    def launch_minecraft(self):
        version = self.selected_version.get()
        player_name = self.username.get()
        
        if not version:
            print("Please select a version!")
            return
            
        if not player_name:
            print("Please enter a username!")
            return
        
        # Create launch options
        options = {
            "username": player_name,
            "uuid": "",
            "token": "",
            "executablePath": os.path.join(self.minecraft_dir, "runtime", "jre-x64", "bin", "java.exe"),
            "jvmArguments": ["-Xmx2G", "-Xms1G"]  # Allocate 2GB RAM
        }
        
        # Get the launch command
        command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
        
        # Launch the game
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Minecraft launched successfully!")
        except Exception as e:
            print(f"Error launching Minecraft: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()
