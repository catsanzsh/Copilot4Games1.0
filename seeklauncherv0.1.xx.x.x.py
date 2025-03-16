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
import webbrowser
import requests  # Import the requests library
from PIL import Image, ImageTk  # For Image handling


# ----------------------------------------
# Constants and Paths
# ----------------------------------------
# Use a more descriptive configuration filename
CONFIG_FILE = "mineseek4k_launcher_config.json"
SKINS_CACHE_DIR = "skins_cache"
DEFAULT_RAM = 4096  # 4GB as a more reasonable default
MAX_RAM = 16384 # Set a more reasonable maximum
DEFAULT_RESOLUTION = "854x480" # Minecraft's default small resolution
LOGO_URL = "https://pbs.twimg.com/profile_images/1673923545998553088/5w-5pvjP_400x400.png" # Example URL - REPLACE WITH A BETTER URL
NEWS_URL = "https://www.minecraft.net/en-us/feeds/community-content/rss"  # Official Minecraft News RSS
FORGE_WEBSITE = "https://files.minecraftforge.net/"
FABRIC_WEBSITE = "https://fabricmc.net/"
OPTIFINE_WEBSITE = "https://optifine.net/downloads"

# ----------------------------------------
# Utility Functions
# ----------------------------------------

def microsoft_login_flow(root):
    """
    Initiates the Microsoft OAuth device-code flow via minecraft_launcher_lib.
    This will prompt the user to visit a Microsoft URL to complete the sign-in.
    After successful sign-in, returns the authentication dictionary if successful,
    otherwise returns None.  Uses improved error handling.
    """
    try:
        # Load any previously saved tokens
        login_data = minecraft_launcher_lib.microsoft_account.load_token_pickle("ms_oauth_token.json")
        if login_data:
            # If we can refresh, do so (it extends the lifetime of the token)
            if minecraft_launcher_lib.microsoft_account.can_refresh_token(login_data):
                login_data = minecraft_launcher_lib.microsoft_account.refresh_token(login_data)
                minecraft_launcher_lib.microsoft_account.save_token_pickle("ms_oauth_token.json", login_data)
                return login_data

        # Otherwise, start a new device-code flow
        login_data = minecraft_launcher_lib.microsoft_account.start_login(server_name="login.live.com")
        code = login_data["user_code"]
        url = login_data["verification_uri"]

        # Improved instructions and option to open the URL
        msg = (
            f"1. Go to: {url}\n2. Enter code: {code}\n\n"
            "After completing sign-in, the launcher will detect your login.\n"
            "Click OK to open the URL in your default browser."
        )
        if messagebox.askokcancel("Microsoft Login", msg):
            webbrowser.open(url)

        # Finish the device-code flow (blocks until user completes login or times out)
        result_data = minecraft_launcher_lib.microsoft_account.finish_login(login_data)
        # Save token so we can refresh next time
        minecraft_launcher_lib.microsoft_account.save_token_pickle("ms_oauth_token.json", result_data)
        return result_data

    except minecraft_launcher_lib.exceptions.AuthenticationException as e:
        messagebox.showerror("Microsoft Login Error", f"Authentication failed: {e}")
        return None
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Microsoft Login Error", f"Network error: {e}")
        return None
    except Exception as e:
        messagebox.showerror("Microsoft Login Error", f"An unexpected error occurred: {e}")
        return None


def fetch_image(url, local_path, resize_to=None):
    """Fetches an image from URL, saves it locally, and returns a PhotoImage object.
       Handles network and file errors gracefully. Optionally resizes the image.
    """
    try:
        if not os.path.exists(local_path):  # Only download if it doesn't exist
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            with open(local_path, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    out_file.write(chunk)

        image = Image.open(local_path)
        if resize_to:
            image = image.resize(resize_to, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from {url}: {e}")
        return None
    except (IOError, OSError) as e:
        print(f"Error opening or saving image {local_path}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during image handling: {e}")
        return None


# ----------------------------------------
# Main Launcher Class
# ----------------------------------------

class MineSeek4KLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("MineSeek4K Launcher")
        self.root.geometry("900x700")
        self.root.minsize(600, 400)  # Set minimum size
        self.root.iconbitmap(default=self.get_icon_path())  # Set the launcher icon

        # Main Minecraft directory
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()

        # Path to config (stores launcher settings)
        self.config_path = os.path.join(self.minecraft_dir, CONFIG_FILE)
        self.skins_cache_dir = os.path.join(self.minecraft_dir, SKINS_CACHE_DIR)
        os.makedirs(self.skins_cache_dir, exist_ok=True)


        # Default settings
        self.default_settings = {
            "java_path": self.find_java(),
            "ram": DEFAULT_RAM,
            "resolution": DEFAULT_RESOLUTION,
            "server_ip": "",
            "active_profile": 0,
            "profiles": [
                {
                    "username": "Player",
                    "auth_method": "offline",  # "offline" or "microsoft"
                    "uuid": "",
                }
            ],
            "last_version": None, # Store the last launched version
            "show_snapshots": False,  # Option to show snapshots
            "show_old_versions": False # Option to show alpha/beta versions.
        }
        self.settings = {}

        # Ensure .minecraft directory exists
        os.makedirs(self.minecraft_dir, exist_ok=True)

        # Load (or create) configuration
        self.load_settings()
        self.current_account_image = None  # Store the current account image

        # ----------------------------------------
        # UI Setup
        # ----------------------------------------
        self.create_main_layout()
        self.load_installed_versions()

        # Load version list from Mojang in background
        Thread(target=self.load_online_versions, daemon=True).start()
        Thread(target=self.load_news, daemon=True).start()  # Load news in the background



    def get_icon_path(self):
        """Returns the correct path to the icon file, handling different OSes."""
        if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
            # If bundled (e.g., with PyInstaller), the icon is in the same directory.
            return os.path.join(sys._MEIPASS, "icon.ico")  # Replace "icon.ico" with your icon filename
        else:
            # If running as a script, assume the icon is in the same directory.
            return os.path.join(os.path.dirname(__file__), "icon.ico")

    def create_main_layout(self):
        """Creates the main layout with top bar, bottom bar, and central notebook."""
        # Top Bar (Logo, Account Info)
        self.top_bar = ttk.Frame(self.root)
        self.top_bar.pack(side="top", fill="x")

        # Logo (using a downloaded image, handled by fetch_image)
        logo_path = os.path.join(self.minecraft_dir, "launcher_logo.png")
        self.logo_image = fetch_image(LOGO_URL, logo_path, resize_to=(100, 100))  # Resize logo
        if self.logo_image:
            logo_label = ttk.Label(self.top_bar, image=self.logo_image)
            logo_label.pack(side="left", padx=5, pady=5)

        # Account/Profile Section (Right side of top bar)
        self.account_frame = ttk.Frame(self.top_bar)
        self.account_frame.pack(side="right", padx=5, pady=5)

        self.account_label = ttk.Label(self.account_frame, text=self.get_current_username())
        self.account_label.pack(side="left")

        self.account_image_label = ttk.Label(self.account_frame)  # Placeholder for account image
        self.account_image_label.pack(side="left", padx=5)
        self.refresh_account_image()  # Load initial account image

        # Account Menu Button (using a more descriptive name)
        self.account_menu_button = ttk.Button(self.account_frame, text="≡", width=3, command=self.show_account_menu)
        self.account_menu_button.pack(side="left")



        # Bottom Bar (Launch Button, Version Selection)
        self.bottom_bar = ttk.Frame(self.root)
        self.bottom_bar.pack(side="bottom", fill="x")

        # Launch Button (Larger and Prominent)
        self.launch_button = ttk.Button(self.bottom_bar, text="PLAY", command=self.launch_minecraft, style="Launch.TButton")
        self.launch_button.pack(side="right", padx=10, pady=5, ipadx=20, ipady=5) # Add padding


        # Version Selection (Combobox, more integrated look)
        self.version_combobox = ttk.Combobox(self.bottom_bar, state="readonly", width=30)
        self.version_combobox.pack(side="right", padx=5, pady=5)
        if self.settings.get("last_version") and self.settings["last_version"] in self.version_combobox["values"]:
            self.version_combobox.set(self.settings["last_version"])

        # Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)

        # Create frames for each tab
        self.play_frame = ttk.Frame(self.notebook)
        self.install_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.skins_frame = ttk.Frame(self.notebook)
        self.news_frame = ttk.Frame(self.notebook)

        # Build out each tab’s content
        self.create_play_tab()
        self.create_install_tab()
        self.create_settings_tab()
        self.create_skins_tab()
        self.create_news_tab()


        # Add tabs to the notebook
        self.notebook.add(self.play_frame, text="Play")
        self.notebook.add(self.install_frame, text="Installations")  # Rename to "Installations"
        self.notebook.add(self.news_frame, text="News")  # Add the News Tab
        self.notebook.add(self.skins_frame, text="Skins")
        self.notebook.add(self.settings_frame, text="Settings")

        self.notebook.pack(expand=True, fill="both")

        # Define a custom style for the launch button
        style = ttk.Style()
        style.configure("Launch.TButton", font=("Arial", 14, "bold"), background="#4CAF50", foreground="white") # Green button
        style.map("Launch.TButton", background=[("active", "#3e8e41")])  # Darker green on hover

        # Initial refresh of profile-related UI
        self.refresh_profile_combobox()



    def show_account_menu(self):
        """Displays a popup menu for account management (Add, Edit, Delete)."""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Add Account", command=self.create_new_profile)
        menu.add_command(label="Edit Account", command=self.edit_profile)
        menu.add_command(label="Remove Account", command=self.delete_profile)
        menu.add_separator()
        menu.add_command(label="Manage Accounts (Microsoft)", command=lambda: webbrowser.open("https://account.microsoft.com/"))
        menu.tk_popup(self.account_menu_button.winfo_rootx(), self.account_menu_button.winfo_rooty() + self.account_menu_button.winfo_height())


    def refresh_account_image(self):
        """Loads and displays the account image (skin head) based on the current profile."""
        profile = self.get_current_profile()
        if not profile:
            return

        size = (32, 32)  # Smaller image size
        if profile["auth_method"] == "microsoft" and profile["uuid"]:
            # Try to fetch from Mojang API (more reliable)
            try:
                response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{profile['uuid']}")
                response.raise_for_status()
                data = response.json()
                # Extract skin URL from the complicated Mojang response (you might need to adjust this)
                for prop in data.get("properties", []):
                    if prop["name"] == "textures":
                        import base64
                        textures = json.loads(base64.b64decode(prop["value"]))
                        skin_url = textures["textures"]["SKIN"]["url"]
                        break
                else:
                    raise ValueError("Skin URL not found in Mojang response")

                image_path = os.path.join(self.skins_cache_dir, f"{profile['uuid']}_head.png")
                self.current_account_image = fetch_image(skin_url, image_path, resize_to=size)

            except (requests.exceptions.RequestException, ValueError, KeyError, json.JSONDecodeError) as e:
                print(f"Error fetching Microsoft skin: {e}")
                self.current_account_image = None  # Fallback if fetching fails
            
        elif profile["auth_method"] == "offline":
              # Use a Steve/Alex skin, or a local cached skin if one is available
              image_path = os.path.join(self.skins_cache_dir, f"{profile['username'].lower()}_head.png")
              if os.path.exists(image_path):
                  try:
                      image = Image.open(image_path)
                      image = image.resize(size, Image.Resampling.LANCZOS)
                      self.current_account_image = ImageTk.PhotoImage(image)
                  except (IOError, OSError) as e:
                      print(f"Error opening cached skin: {e}")
                      self.current_account_image = None
              else:
                  # Fallback to Steve
                  self.current_account_image = self.load_steve_skin(size) # Load Steve
        else:
            self.current_account_image = None

        if self.current_account_image:
            self.account_image_label.config(image=self.current_account_image)
        else:
            self.account_image_label.config(image="")  # Clear if no image
            

    def load_steve_skin(self, size):
        """Loads a built-in Steve skin as a fallback"""
        try:
            # Assuming 'steve.png' is in the same directory as the script.
            image_path = os.path.join(os.path.dirname(__file__), "steve.png")
            image = Image.open(image_path)
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Error loading Steve skin: {e}")
            return None


    def get_current_username(self):
        """Retrieves the username of the currently selected profile."""
        profile = self.get_current_profile()
        return profile["username"] if profile else "Guest"


    def get_current_profile(self):
        """Retrieves the currently selected profile from the combobox."""
        return self.settings.get("profiles", [{}])[self.settings.get("active_profile", 0)]


    def create_new_profile(self):
        """Creates a new profile with offline authentication."""
        new_profile = {
            "username": "Player",
            "auth_method": "offline", # "offline" or "microsoft"
            "uuid": "",
        }
        self.settings["profiles"].append(new_profile)
        self.settings["active_profile"] = len(self.settings["profiles"]) - 1
        self.save_settings()
        
