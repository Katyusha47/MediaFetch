import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from pathlib import Path
import yt_dlp
import json

# App version
VERSION = "0.1.1"
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
        
        # URL Input
        url_label = ctk.CTkLabel(
            main_frame,
            text="Enter URL:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        url_label.grid(row=2, column=0, pady=(10, 5), sticky="w", padx=20)
        
        self.url_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Paste your URL here (YouTube, Instagram, TikTok, etc.)",
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.url_entry.grid(row=3, column=0, pady=(0, 20), sticky="ew", padx=20)
        self.url_entry.bind('<FocusOut>', self.detect_formats)
        
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
        
        # Progress Section
        self.progress_frame = ctk.CTkFrame(main_frame)
        self.progress_frame.grid(row=6, column=0, pady=(0, 20), sticky="ew", padx=20)
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
        url = self.url_entry.get().strip()
        if not url or url.startswith("http") == False:
            return
            
        # Run detection in background
        thread = threading.Thread(target=self.detect_formats_thread, args=(url,))
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
            
            # Format-specific options
            if "Audio" in format_choice:
                # Determine audio quality
                audio_quality = '320'  # Default best quality
                if 'kbps' in quality:
                    audio_quality = quality.split()[0]  # Extract number from "320 kbps"
                
                # Audio download
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
                # Video download with fps handling
                if quality == "Best":
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                elif "60fps" in quality:
                    # 60fps specific formats
                    if "4K" in quality:
                        ydl_opts['format'] = 'bestvideo[height<=2160][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]'
                    elif "1440p" in quality:
                        ydl_opts['format'] = 'bestvideo[height<=1440][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]'
                    elif "1080p" in quality:
                        ydl_opts['format'] = 'bestvideo[height<=1080][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]'
                    elif "720p" in quality:
                        ydl_opts['format'] = 'bestvideo[height<=720][fps>=60][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
                else:
                    # Standard formats (30fps or best available)
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
                ydl.download([url])
            
            # Success
            self.status_label.configure(text="Download completed successfully!")
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="100%")
            messagebox.showinfo("Success", "Download completed successfully!")
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Download failed:\n{str(e)}")
            
        finally:
            self.is_downloading = False
            self.download_btn.configure(
                text="Start Download",
                state="normal"
            )
            
    def start_download(self):
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL!")
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
        
        # Start download in separate thread
        thread = threading.Thread(target=self.download_thread, args=(url,))
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
