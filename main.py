import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from pathlib import Path
import yt_dlp
import json
import time
import urllib.request
import urllib.error

# App version
VERSION = "0.1.2"
# Accent color: try to derive from `icon.ico` if available, else fallback
def _hex_from_rgb(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def _darken(hex_color, amount=0.2):
    # Darken a hex color by amount (0..1)
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return _hex_from_rgb((r, g, b))

ACCENT_COLOR = "#b30000"
HOVER_COLOR = _darken(ACCENT_COLOR, 0.2)

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("MediaFetch")
        self.geometry("900x750")
        self.minsize(800, 700)
        self.resizable(True, True)
        
        # Icon loading disabled per user request (do not load icon.ico at runtime)
        
        # Variables
        self.download_path = str(Path.home() / "Downloads")
        self.is_downloading = False
        self.config_path = Path.home() / ".mediafetch_config.json"
        self.history_path = Path.home() / ".mediafetch_history.json"
        self.config = self.load_config()
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main frame
        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="MediaFetch",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="n")
        
        subtitle = ctk.CTkLabel(
            main_frame,
            text="Download videos, audio, and more from any platform",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle.grid(row=1, column=0, pady=(0, 30), sticky="n")
        
        # URL Input (supports multiple URLs / batch)
        url_label = ctk.CTkLabel(
            main_frame,
            text="Enter URL(s):",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        url_label.grid(row=2, column=0, pady=(10, 5), sticky="w", padx=20)

        # Multiline textbox for batch URLs (one per line)
        self.url_text = ctk.CTkTextbox(
            main_frame,
            height=90,
            font=ctk.CTkFont(size=13)
        )
        self.url_text.grid(row=3, column=0, pady=(0, 20), sticky="ew", padx=20)
        # Placeholder behavior (CTkTextbox doesn't have native placeholder)
        self.url_placeholder = "Paste one or more URLs (one per line)"
        self.url_placeholder_active = True
        self.url_text.insert("0.0", self.url_placeholder)
        try:
            self.url_text.configure(text_color='gray')
        except Exception:
            pass
        # Bind focus events: clear placeholder on focus in, detect formats on focus out
        self.url_text.bind('<FocusIn>', self._on_url_focus_in)
        self.url_text.bind('<FocusOut>', self._on_url_focus_out)
        
        # Options Frame
        options_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        options_frame.grid(row=4, column=0, pady=(0, 20), sticky="ew", padx=20)
        options_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Format Selection
        format_label = ctk.CTkLabel(
            options_frame,
            text="Format:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        format_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        self.format_var = ctk.StringVar(value="Video (MP4)")
        self.format_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                "Video (MP4)",
                "Video (MKV)",
                "Audio (MP3)",
                "Audio (FLAC)",
                "Audio (WAV)",
                "Audio (M4A)"
            ],
            variable=self.format_var,
            command=self.update_quality_options,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT_COLOR,
            button_color=ACCENT_COLOR
        )
        self.format_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        # Quality Selection
        quality_label = ctk.CTkLabel(
            options_frame,
            text="Quality:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        quality_label.grid(row=0, column=1, pady=(0, 5), sticky="w")
        
        self.quality_var = ctk.StringVar(value="Best")
        self.quality_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["Best", "1080p", "720p", "480p", "360p"],
            variable=self.quality_var,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT_COLOR,
            button_color=ACCENT_COLOR
        )
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        
        # Download Path
        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.grid(row=5, column=0, pady=(0, 20), sticky="ew", padx=20)
        path_frame.grid_columnconfigure(0, weight=1)
        
        path_label = ctk.CTkLabel(
            path_frame,
            text="Save to:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        path_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        path_display_frame = ctk.CTkFrame(path_frame, height=40)
        path_display_frame.grid(row=1, column=0, sticky="ew")
        path_display_frame.grid_columnconfigure(0, weight=1)
        
        self.path_label = ctk.CTkLabel(
            path_display_frame,
            text=self.download_path,
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.path_label.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        browse_btn = ctk.CTkButton(
            path_display_frame,
            text="Browse",
            width=100,
            command=self.browse_folder,
            font=ctk.CTkFont(size=13),
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR
        )
        browse_btn.grid(row=0, column=1, padx=10)

        # Extra Options Frame
        extra_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        extra_frame.grid(row=6, column=0, pady=(0, 10), sticky="ew", padx=20)
        extra_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Subtitles checkbox + language
        self.subs_var = ctk.BooleanVar(value=False)
        subs_cb = ctk.CTkCheckBox(extra_frame, text="Download subtitles", variable=self.subs_var)
        subs_cb.grid(row=0, column=0, sticky="w")

        # Subtitle language selection (non-editable dropdown)
        self.subs_lang_var = ctk.StringVar(value="en")
        subs_lang_menu = ctk.CTkOptionMenu(
            extra_frame,
            values=["auto","en","es","fr","de","pt","ru","zh-Hans","ja","ko"],
            variable=self.subs_lang_var,
            width=120,
            fg_color=ACCENT_COLOR,
            button_color=ACCENT_COLOR
        )
        subs_lang_menu.grid(row=0, column=1, sticky="w")

        # Thumbnail extraction
        self.thumb_var = ctk.BooleanVar(value=False)
        thumb_cb = ctk.CTkCheckBox(extra_frame, text="Extract thumbnail", variable=self.thumb_var)
        thumb_cb.grid(row=0, column=2, sticky="w")

        # Theme toggle
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_btn = ctk.CTkButton(extra_frame, text="Toggle Theme", command=self.toggle_theme, width=120, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR)
        theme_btn.grid(row=1, column=0, pady=(8,0), sticky="w")

        # History and Update buttons
        history_btn = ctk.CTkButton(extra_frame, text="History", width=100, command=self.show_history, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR)
        history_btn.grid(row=1, column=1, pady=(8,0))

        update_btn = ctk.CTkButton(extra_frame, text="Check for updates", width=160, command=lambda: self.check_for_updates(show_popup=True), fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR)
        update_btn.grid(row=1, column=2, pady=(8,0), sticky="e")
        
        # Progress Section
        self.progress_frame = ctk.CTkFrame(main_frame)
        self.progress_frame.grid(row=7, column=0, pady=(0, 20), sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=13)
        )
        self.status_label.grid(row=0, column=0, pady=(15, 10), sticky="w", padx=15)
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=20,
            progress_color=ACCENT_COLOR
        )
        self.progress_bar.grid(row=1, column=0, pady=(0, 10), sticky="ew", padx=15)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="0%",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=2, column=0, pady=(0, 15), sticky="w", padx=15)
        
        # Download Button
        self.download_btn = ctk.CTkButton(
            main_frame,
            text="Start Download",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_download,
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR
        )
        self.download_btn.grid(row=7, column=0, pady=(0, 20), sticky="ew", padx=20)

        # About Button
        about_btn = ctk.CTkButton(
            main_frame,
            text="About",
            width=120,
            command=self.show_about,
            font=ctk.CTkFont(size=12),
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR
        )
        about_btn.grid(row=8, column=0, pady=(0, 10), sticky="e", padx=20)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.configure(text=folder)
            
    def show_about(self):
        """Show About dialog with app name and version"""
        try:
            message = f"MediaFetch\nVersion: {VERSION}\n\nA simple media downloader powered by yt-dlp."
            messagebox.showinfo("About MediaFetch", message)
        except Exception:
            messagebox.showinfo("About", "MediaFetch")
            
    def update_quality_options(self, choice):
        """Update quality options based on format selection"""
        if "Audio" in choice:
            # Audio quality options
            audio_qualities = ["Best", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]
            self.quality_menu.configure(values=audio_qualities)
            self.quality_var.set("Best")
        else:
            # Video quality options
            video_qualities = [
                "Best",
                "4K 60fps",
                "4K (2160p)",
                "1440p 60fps",
                "1440p",
                "1080p 60fps",
                "1080p",
                "720p 60fps",
                "720p",
                "480p",
                "360p"
            ]
            self.quality_menu.configure(values=video_qualities)
            self.quality_var.set("Best")
            
    def detect_formats(self, event=None):
        """Detect available formats when URL is pasted"""
        # If placeholder is showing, don't attempt detection
        if getattr(self, 'url_placeholder_active', False):
            return

        # Use the first non-empty URL from the textbox for detection
        text = self.url_text.get("0.0", "end").strip()
        first_url = None
        for line in text.splitlines():
            line = line.strip()
            if line:
                first_url = line
                break
        if not first_url or not first_url.startswith("http"):
            return
            
        # Run detection in background
        thread = threading.Thread(target=self.detect_formats_thread, args=(first_url,))
        thread.daemon = True
        thread.start()
        
    def detect_formats_thread(self, url):
        """Background thread to detect available formats"""
        try:
            self.status_label.configure(text="Detecting available formats...")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    # Get available video qualities
                    available_heights = set()
                    available_fps = set()
                    
                    if 'formats' in info:
                        for fmt in info['formats']:
                            if fmt.get('height'):
                                available_heights.add(fmt['height'])
                            if fmt.get('fps'):
                                available_fps.add(fmt['fps'])
                    
                    # Build quality list based on available formats
                    video_qualities = ["Best"]
                    
                    # Check for 60fps support
                    has_60fps = any(fps >= 60 for fps in available_fps)
                    
                    # Add qualities that are available
                    if 2160 in available_heights:
                        if has_60fps:
                            video_qualities.append("4K 60fps")
                        video_qualities.append("4K (2160p)")
                    if 1440 in available_heights:
                        if has_60fps:
                            video_qualities.append("1440p 60fps")
                        video_qualities.append("1440p")
                    if 1080 in available_heights:
                        if has_60fps:
                            video_qualities.append("1080p 60fps")
                        video_qualities.append("1080p")
                    if 720 in available_heights:
                        if has_60fps:
                            video_qualities.append("720p 60fps")
                        video_qualities.append("720p")
                    if 480 in available_heights:
                        video_qualities.append("480p")
                    if 360 in available_heights or 240 in available_heights:
                        video_qualities.append("360p")
                    
                    # Update quality menu if video format is selected
                    if "Video" in self.format_var.get():
                        self.quality_menu.configure(values=video_qualities)
                        self.quality_var.set("Best")
                    
                    self.status_label.configure(text=f"Ready to download (Max: {max(available_heights) if available_heights else 'Unknown'}p)")
                else:
                    self.status_label.configure(text="Ready to download")
                    
        except Exception as e:
            # If detection fails, just keep default options
            self.status_label.configure(text="Ready to download")
            pass

    def _on_url_focus_in(self, event=None):
        try:
            if getattr(self, 'url_placeholder_active', False):
                # Clear placeholder
                self.url_text.delete('0.0', 'end')
                # set normal text color
                try:
                    self.url_text.configure(text_color=None)
                except Exception:
                    pass
                self.url_placeholder_active = False
        except Exception:
            pass

    def _on_url_focus_out(self, event=None):
        try:
            content = self.url_text.get('0.0', 'end').strip()
            if not content:
                # restore placeholder
                self.url_text.delete('0.0', 'end')
                self.url_text.insert('0.0', self.url_placeholder)
                try:
                    self.url_text.configure(text_color='gray')
                except Exception:
                    pass
                self.url_placeholder_active = True
            else:
                # User entered something; run detection
                self.url_placeholder_active = False
                # call detect_formats to update qualities
                self.detect_formats()
        except Exception:
            pass
            
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Extract percentage
            percentage_str = d.get('_percent_str', '0%').strip()
            try:
                percentage = float(percentage_str.replace('%', ''))
                self.progress_bar.set(percentage / 100)
                self.progress_label.configure(text=f"{percentage:.1f}%")
                
                # Update status with speed and ETA
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self.status_label.configure(
                    text=f"Downloading... Speed: {speed} | ETA: {eta}"
                )
            except:
                pass
                
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Processing... Almost done!")
            
    def download_thread(self, url):
        # Support downloading a single url (string) or an iterable of urls
        urls = []
        if isinstance(url, (list, tuple)):
            urls = url
        else:
            urls = [url]

        for single_url in urls:
            try:
                # Determine format and quality options
                format_choice = self.format_var.get()
                quality = self.quality_var.get()

                # Base options
                ydl_opts = {
                    'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'quiet': False,
                    'no_warnings': False,
                }

                # Subtitles
                if self.subs_var.get():
                    lang = self.subs_lang_var.get().strip() or 'en'
                    ydl_opts['writesubtitles'] = True
                    ydl_opts['subtitleslangs'] = [lang]
                    ydl_opts['writeautomaticsub'] = True

                # Thumbnail
                if self.thumb_var.get():
                    ydl_opts['writethumbnail'] = True

                # Format-specific options (audio/video)
                if "Audio" in format_choice:
                    audio_quality = '320'
                    if 'kbps' in quality:
                        audio_quality = quality.split()[0]

                    if "MP3" in format_choice:
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': audio_quality,
                            }],
                        })
                    elif "FLAC" in format_choice:
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'flac',
                            }],
                        })
                    elif "WAV" in format_choice:
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'wav',
                            }],
                        })
                    elif "M4A" in format_choice:
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'm4a',
                                'preferredquality': audio_quality,
                            }],
                        })
                else:
                    # Video download with fps handling (same logic as before)
                    if quality == "Best":
                        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    elif "60fps" in quality:
                        if "4K" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=2160][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]'
                        elif "1440p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=1440][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]'
                        elif "1080p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=1080][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]'
                        elif "720p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=720][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
                    else:
                        if "4K" in quality or "2160p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]'
                        elif "1440p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]'
                        elif "1080p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]'
                        elif "720p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]'
                        elif "480p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]'
                        elif "360p" in quality:
                            ydl_opts['format'] = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]'

                    if "MKV" in format_choice:
                        ydl_opts['merge_output_format'] = 'mkv'
                    else:
                        ydl_opts['merge_output_format'] = 'mp4'

                # Download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([single_url])

                # Success: record history entry
                self.save_history_entry({
                    'url': single_url,
                    'time': int(time.time()),
                    'status': 'success',
                    'path': self.download_path,
                    'format': format_choice,
                    'quality': quality
                })
                self.status_label.configure(text="Download completed successfully!")
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="100%")

            except Exception as e:
                # Record failure in history
                self.save_history_entry({
                    'url': single_url,
                    'time': int(time.time()),
                    'status': 'error',
                    'error': str(e)
                })
                self.status_label.configure(text=f"Error: {str(e)}")
                messagebox.showerror("Error", f"Download failed:\n{str(e)}")

        # Finalize
        self.is_downloading = False
        self.download_btn.configure(
            text="Start Download",
            state="normal"
        )
            
    def start_download(self):
        # Gather URLs from multiline textbox
        text = self.url_text.get("0.0", "end").strip()
        urls = [line.strip() for line in text.splitlines() if line.strip()]

        if not urls:
            messagebox.showwarning("Warning", "Please enter at least one URL!")
            return
            
        if self.is_downloading:
            messagebox.showwarning("Warning", "Download already in progress!")
            return
        
        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.status_label.configure(text="Starting download...")
        
        # Disable button
        self.download_btn.configure(
            text="Downloading...",
            state="disabled"
        )
        
        self.is_downloading = True
        
        # Start download in separate thread (pass the list)
        thread = threading.Thread(target=self.download_thread, args=(urls,))
        thread.daemon = True
        thread.start()

    # ------------------ Configuration, history, and utilities ------------------
    def load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def toggle_theme(self):
        current = self.config.get('theme', 'dark')
        new = 'light' if current == 'dark' else 'dark'
        ctk.set_appearance_mode(new)
        self.config['theme'] = new
        self.save_config()

    def load_history(self):
        try:
            if self.history_path.exists():
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def save_history_entry(self, entry):
        hist = self.load_history()
        hist.insert(0, entry)
        # Keep only last 200 entries
        hist = hist[:200]
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(hist, f, indent=2)
        except Exception:
            pass

    def show_history(self):
        hist = self.load_history()
        win = ctk.CTkToplevel(self)
        win.title('Download History')
        win.geometry('700x400')
        # Use a selectable Listbox (monospace) so user can highlight and re-run entries
        frame = ctk.CTkFrame(win, fg_color='transparent')
        frame.pack(fill='both', expand=True, padx=10, pady=(10, 6))

        # Use native tkinter Listbox for selection behavior
        listbox = tk.Listbox(frame, font=("Courier New", 11), activestyle='none')
        scrollbar = tk.Scrollbar(frame, orient='vertical', command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        if not hist:
            listbox.insert('end', 'No history yet.')
            listbox.configure(state='disabled')
            return

        # Populate listbox with history lines
        for item in hist:
            t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item.get('time', 0)))
            status = item.get('status', 'unknown')
            url = item.get('url', '')
            path = item.get('path', '')
            fmt = item.get('format', '')
            q = item.get('quality', '')
            if status == 'success':
                listbox.insert('end', f"[{t}] OK  {url} -> {path} ({fmt} {q})")
            else:
                err = item.get('error', '')
                listbox.insert('end', f"[{t}] ERR {url} -> {err}")

        # Selected URL storage
        selected = {'url': None}

        import re
        def parse_url_from_line(line):
            m = re.search(r"(https?://\S+)", line)
            if m:
                return m.group(1)
            return None

        def on_double_click(event=None):
            try:
                idx = listbox.nearest(event.y)
                line = listbox.get(idx)
                url = parse_url_from_line(line)
                if url:
                    selected['url'] = url
                    if messagebox.askyesno('Re-run', f'Re-run this URL?\n{url}'):
                        self._run_url(url)
            except Exception:
                pass

        def on_select(event=None):
            sel = listbox.curselection()
            if sel:
                line = listbox.get(sel[0])
                selected['url'] = parse_url_from_line(line)
            else:
                selected['url'] = None

        listbox.bind('<Double-Button-1>', on_double_click)
        listbox.bind('<<ListboxSelect>>', on_select)

        # Buttons: Re-run selected, Clear history
        btn_frame = ctk.CTkFrame(win, fg_color='transparent')
        btn_frame.pack(fill='x', padx=10, pady=(6,10))

        def on_rerun_btn():
            url = selected.get('url')
            if url:
                if messagebox.askyesno('Re-run', f'Re-run this URL?\n{url}'):
                    self._run_url(url)
            else:
                messagebox.showinfo('No selection', 'Select a history line to re-run.')

        def on_clear_btn():
            if messagebox.askyesno('Clear history', 'Clear all download history?'):
                try:
                    if self.history_path.exists():
                        self.history_path.unlink()
                except Exception:
                    pass
                listbox.delete(0, 'end')
                listbox.insert('end', 'No history yet.')
                listbox.configure(state='disabled')

        rerun_btn = ctk.CTkButton(btn_frame, text='Re-run Selected', width=140, command=on_rerun_btn, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR)
        rerun_btn.pack(side='left', padx=(0,8))

        clear_btn = ctk.CTkButton(btn_frame, text='Clear History', width=120, command=on_clear_btn, fg_color=ACCENT_COLOR, hover_color=HOVER_COLOR)
        clear_btn.pack(side='left')

    def check_for_updates(self, show_popup=False):
        # Check GitHub releases for a newer tag
        try:
            url = 'https://api.github.com/repos/Katyusha47/MediaFetch/releases/latest'
            req = urllib.request.Request(url, headers={'User-Agent': 'MediaFetch-Updater'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.load(resp)
                tag = data.get('tag_name') or data.get('name')
                if tag and tag.startswith('v'):
                    latest = tag.lstrip('v')
                else:
                    latest = tag
                if latest and latest != VERSION:
                    if show_popup:
                        messagebox.showinfo('Update available', f'New version available: {tag} (current: {VERSION})')
                    return True, tag
                else:
                    if show_popup:
                        messagebox.showinfo('Up to date', 'You are running the latest version.')
                    return False, None
        except Exception:
            if show_popup:
                messagebox.showwarning('Update check failed', 'Could not check for updates (network error).')
            return False, None

    def _run_url(self, url):
        # Helper to run a single URL download (invoked from history)
        if self.is_downloading:
            messagebox.showwarning('Busy', 'A download is already in progress.')
            return

        # Reset progress and UI like start_download
        self.progress_bar.set(0)
        self.progress_label.configure(text='0%')
        self.status_label.configure(text='Starting download...')
        self.download_btn.configure(text='Downloading...', state='disabled')
        self.is_downloading = True

        thread = threading.Thread(target=self.download_thread, args=([url],))
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
