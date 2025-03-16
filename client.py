import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import minecraft_launcher_lib
import subprocess
import os
import json
from threading import Thread

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("PyLauncher")
        self.root.geometry("800x600")

        # Where Minecraft files are stored
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()

        # Launcher settings (will be saved/loaded to file)
        self.settings = {
            "java_path": "",
            "ram": "4096",            # in MB
            "resolution": "1280x720",
            "server_ip": ""
        }

        # UI variables
        self.selected_version = tk.StringVar()
        self.username = tk.StringVar(value="Player")
        self.modloader_var = tk.StringVar(value="Vanilla")  # For installations
        self.download_progress = tk.DoubleVar()

        # Create the notebook (tabs) and load settings
        self.create_notebook()
        self.load_settings()       # Load any saved settings
        self.load_installed_versions()  # Populate the "Play" tab combobox with installed versions

    def create_notebook(self):
        """Create tabs for Play, Installations, Skins, and Settings."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # Play Tab
        self.play_frame = ttk.Frame(self.notebook)
        self.create_play_tab()
        self.notebook.add(self.play_frame, text="Play")

        # Installations Tab
        self.install_frame = ttk.Frame(self.notebook)
        self.create_install_tab()
        self.notebook.add(self.install_frame, text="Installations")

        # Skins Tab
        self.skin_frame = ttk.Frame(self.notebook)
        self.create_skin_tab()
        self.notebook.add(self.skin_frame, text="Skins")

        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.create_settings_tab()
        self.notebook.add(self.settings_frame, text="Settings")

    # --------------------------------------------------
    # -------------------- PLAY TAB --------------------
    # --------------------------------------------------
    def create_play_tab(self):
        """Create the Play tab UI."""
        # Version selection
        ttk.Label(self.play_frame, text="Version:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.version_combobox = ttk.Combobox(
            self.play_frame, textvariable=self.selected_version, state="readonly"
        )
        self.version_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Username
        ttk.Label(self.play_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(self.play_frame, textvariable=self.username).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Server IP
        ttk.Label(self.play_frame, text="Server IP:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.server_entry = ttk.Entry(self.play_frame)
        self.server_entry.insert(0, self.settings.get("server_ip", ""))
        self.server_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Launch Button
        launch_button = ttk.Button(self.play_frame, text="Launch Minecraft", command=self.launch_minecraft)
        launch_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        # Console Output
        self.console = tk.Text(self.play_frame, height=10, state="disabled")
        self.console.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.play_frame.grid_rowconfigure(4, weight=1)
        self.play_frame.grid_columnconfigure(1, weight=1)

    def launch_minecraft(self):
        """Launch Minecraft with selected version and options."""
        version = self.selected_version.get()
        if not version:
            messagebox.showerror("Error", "Please select a version to launch.")
            return

        # Update server IP in settings
        self.settings["server_ip"] = self.server_entry.get()

        # Prepare JVM arguments
        try:
            ram_int = int(self.settings["ram"])
        except ValueError:
            ram_int = 4096  # fallback
        jvm_args = [
            f"-Xmx{ram_int}M",
            f"-Xms{ram_int}M",  # or (ram_int // 2) if you prefer
            f"-Dminecraft.resolution={self.settings['resolution']}"
        ]

        options = {
            "username": self.username.get(),
            "jvmArguments": jvm_args
        }

        if self.settings["java_path"]:
            options["executablePath"] = self.settings["java_path"]

        # If user typed a server IP, auto-join
        server_ip = self.server_entry.get().strip()
        if server_ip:
            options["server"] = server_ip

        try:
            command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)

            # Create a subprocess to launch the game
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Read process output in a separate thread
            Thread(target=self._read_launcher_output, args=(process,), daemon=True).start()
            self.log("Launching Minecraft...")

        except Exception as e:
            self.log(f"Launch error: {str(e)}")

    def _read_launcher_output(self, process):
        """Reads launcher stdout/stderr in the background and displays it in the console."""
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                self.log(line.rstrip())

        # After stdout ends, read stderr too
        for line in process.stderr:
            self.log(line.rstrip())

    # ----------------------------------------------------
    # ---------------- INSTALLATIONS TAB -----------------
    # ----------------------------------------------------
    def create_install_tab(self):
        """Create the Installations tab UI."""
        # Modloader Selection
        ttk.Label(self.install_frame, text="Modloader:").grid(row=0, column=0, padx=5, pady=5, sticky="e")

        modloader_combobox = ttk.Combobox(
            self.install_frame,
            textvariable=self.modloader_var,
            values=["Vanilla", "Forge", "Fabric", "OptiFine"],
            state="readonly"
        )
        modloader_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        modloader_combobox.current(0)

        # Install Button
        install_button = ttk.Button(self.install_frame, text="Install Version", command=self.install_version)
        install_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Version Tree (display remote releases)
        columns = ("type", "release")
        self.version_tree = ttk.Treeview(self.install_frame, columns=columns, show="headings")
        self.version_tree.heading("type", text="Type")
        self.version_tree.heading("release", text="Release Date")
        self.version_tree.column("type", width=80, anchor="center")
        self.version_tree.column("release", width=140, anchor="center")

        # We'll store the version ID in the "text" field
        self.version_tree.grid(row=1, column=0, columnspan=3, sticky="nsew")

        self.install_frame.grid_rowconfigure(1, weight=1)
        self.install_frame.grid_columnconfigure(0, weight=1)

        # Load remote version list in a background thread
        Thread(target=self.load_online_versions, daemon=True).start()

    def load_online_versions(self):
        """Fetch the official list of Minecraft releases from Mojang and populate the TreeView."""
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            # Only show official releases (exclude snapshots, betas, etc.)
            for version in versions:
                if version["type"] == "release":
                    self.version_tree.insert(
                        "",
                        "end",
                        text=version["id"],
                        values=(version["type"], version["releaseTime"])
                    )
        except Exception as e:
            self.log(f"Error loading versions: {str(e)}")

    def install_version(self):
        """Install the selected version with the chosen modloader."""
        selection = self.version_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Please select a version to install.")
            return

        version_id = self.version_tree.item(selection[0])["text"]
        modloader = self.modloader_var.get()

        def do_install():
            try:
                if modloader == "Forge":
                    # Installs the Forge version for the chosen MC version
                    minecraft_launcher_lib.forge.install_forge_version(version_id, self.minecraft_dir)
                    self.log(f"Installed Forge for Minecraft {version_id}")
                elif modloader == "Fabric":
                    minecraft_launcher_lib.fabric.install_fabric(version_id, self.minecraft_dir)
                    self.log(f"Installed Fabric for Minecraft {version_id}")
                elif modloader == "OptiFine":
                    # Placeholder: minecraft-launcher-lib does not fully automate OptiFine installs.
                    # One approach is to download the OptiFine installer and run it, or use partial logic.
                    # We'll just log for now:
                    self.log("OptiFine installation is not fully automated. Manual steps may be required.")
                else:
                    # Vanilla install
                    minecraft_launcher_lib.install.install_minecraft_version(version_id, self.minecraft_dir)
                    self.log(f"Installed Vanilla Minecraft {version_id}")

                # After successful install, refresh the "Play" tab's combobox
                self.load_installed_versions()

            except Exception as e:
                self.log(f"Installation error: {str(e)}")

        Thread(target=do_install, daemon=True).start()

    def load_installed_versions(self):
        """Scan the local .minecraft folder for installed versions and populate the play combobox."""
        try:
            installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
            version_ids = [v["id"] for v in installed]
            self.version_combobox["values"] = version_ids

            # If none selected, pick the first in list (optional)
            if version_ids and not self.selected_version.get():
                self.selected_version.set(version_ids[0])
        except Exception as e:
            self.log(f"Error loading installed versions: {str(e)}")

    # --------------------------------------------------
    # -------------------- SKIN TAB --------------------
    # --------------------------------------------------
    def create_skin_tab(self):
        """Create the Skins tab UI."""
        ttk.Label(self.skin_frame, text="Current Skin:").grid(row=0, column=0, padx=5, pady=5)
        self.skin_canvas = tk.Canvas(self.skin_frame, width=64, height=64, bg="white")
        self.skin_canvas.grid(row=0, column=1, padx=5, pady=5)

        upload_button = ttk.Button(self.skin_frame, text="Upload Skin", command=self.upload_skin)
        upload_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        # If you want to display the current skin image, you'd need additional logic for that
        # (fetching player's skin or local image). Right now, it's just a placeholder.

    def upload_skin(self):
        """Upload a PNG file as the player's skin (placeholder logic)."""
        file_path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if file_path:
            # For offline mode, there's no official server to upload to.
            # If you have your own server or an API, implement it here.
            # For now, just log that the user selected a skin.
            self.log(f"Selected skin file: {file_path}")

    # ----------------------------------------------------
    # ------------------- SETTINGS TAB -------------------
    # ----------------------------------------------------
    def create_settings_tab(self):
        """Create the Settings tab UI."""
        # Java Path
        ttk.Label(self.settings_frame, text="Java Path:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.java_path_entry = ttk.Entry(self.settings_frame)
        self.java_path_entry.insert(0, self.settings["java_path"])
        self.java_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        java_browse_btn = ttk.Button(
            self.settings_frame, text="Browse", command=self.browse_java
        )
        java_browse_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # RAM Allocation
        ttk.Label(self.settings_frame, text="RAM (MB):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.ram_spinbox = ttk.Spinbox(self.settings_frame, from_=1024, to=65536)
        self.ram_spinbox.delete(0, "end")
        self.ram_spinbox.insert(0, self.settings["ram"])
        self.ram_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Resolution
        ttk.Label(self.settings_frame, text="Resolution (WxH):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.resolution_entry = ttk.Entry(self.settings_frame)
        self.resolution_entry.insert(0, self.settings["resolution"])
        self.resolution_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Save Button
        save_btn = ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings)
        save_btn.grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        # Layout weights
        self.settings_frame.columnconfigure(1, weight=1)

    def browse_java(self):
        """Browse for a custom Java executable."""
        path = filedialog.askopenfilename(title="Select Java Executable")
        if path:
            self.java_path_entry.delete(0, tk.END)
            self.java_path_entry.insert(0, path)

    def save_settings(self):
        """Save current settings to a JSON file in the Minecraft directory."""
        self.settings["java_path"] = self.java_path_entry.get()
        self.settings["ram"] = self.ram_spinbox.get()
        self.settings["resolution"] = self.resolution_entry.get()

        # Also save the server IP from the Play tab
        self.settings["server_ip"] = self.server_entry.get()

        settings_path = os.path.join(self.minecraft_dir, "PyLauncher_settings.json")
        try:
            with open(settings_path, "w") as f:
                json.dump(self.settings, f, indent=4)
            self.log("Settings saved successfully.")
        except Exception as e:
            self.log(f"Could not save settings: {str(e)}")

    def load_settings(self):
        """Load launcher settings from a JSON file, if it exists."""
        settings_path = os.path.join(self.minecraft_dir, "PyLauncher_settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    loaded = json.load(f)
                self.settings.update(loaded)
            except Exception as e:
                self.log(f"Could not load settings: {str(e)}")

    # ----------------------------------------------------
    # ------------------ LOGGING HELPER ------------------
    # ----------------------------------------------------
    def log(self, message):
        """Append a message to the console text box."""
        self.console.config(state="normal")
        self.console.insert("end", message + "\n")
        self.console.config(state="disabled")
        self.console.see("end")


if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()
