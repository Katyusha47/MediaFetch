# MediaFetch

A modern, sleek desktop application to download videos and audio from ANY platform!

## Features

- **Universal Support**: YouTube, Instagram, TikTok, Twitter, Facebook, and 1000+ sites
- **Multiple Formats**: MP4, MKV, MP3, FLAC, WAV, M4A
- **Quality Options**: Best, 1080p, 720p, 480p, 360p

## Quick Start

### 1. Install Dependencies

First, make sure you have Python 3.8+ installed. Then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg (Required for audio conversion)

**Windows:**
- Download from: https://www.gyan.dev/ffmpeg/builds/
- Extract and add to PATH, or place in the same folder as the app

**Or use Chocolatey:**
```powershell
choco install ffmpeg
```

**Or use winget:**
```powershell
winget install ffmpeg
```

### 3. Run the App

```bash
python main.py
```
Or just run the .exe file.
The .exe will be in the `dist` folder!

## Supported Platforms

- YouTube (videos, playlists, shorts)
- Instagram (posts, reels, stories)
- TikTok
- Twitter/X
- Facebook
- Reddit
- Vimeo
- Dailymotion
- SoundCloud
- Twitch
- And 1000+ more!

## How to Use

1. **Paste URL**: Copy any video/audio URL and paste it
2. **Select Format**: Choose between video (MP4/MKV) or audio (MP3/FLAC/WAV/M4A)
3. **Choose Quality**: Pick your preferred quality
4. **Set Download Location**: Choose where to save the file
5. **Click Download**: Sit back and watch the progress!


## Troubleshooting

**"No module named 'customtkinter'"**
```bash
pip install customtkinter
```

**"ERROR: unable to download video data: HTTP Error 403"**
- The site may be blocking yt-dlp. Try updating: `pip install --upgrade yt-dlp`

**Audio conversion not working**
- Install FFmpeg (see installation instructions above)

**App freezes during download**
- This shouldn't happen! The app uses threading to keep UI responsive

## Future Features

- [ ] Batch download (multiple URLs)
- [ ] Playlist support
- [ ] Subtitle download
- [ ] Thumbnail extraction
- [ ] Video trimming/editing
- [ ] Auto-update checker
- [ ] Download history
- [ ] Themes (light mode)

## License

MIT License - Do whatever you want with it!

## Contributing

Feel free to fork, modify, and make it even better!
