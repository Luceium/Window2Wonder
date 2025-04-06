#!/usr/bin/env python3

import argparse
import subprocess
import re
from typing import Optional, Dict, Callable
import os

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Play YouTube videos from the command line")
    parser.add_argument("--url", type=str, help="YouTube URL to play")
    parser.add_argument("--player", choices=["vlc", "mpv", "omxplayer"], default="mpv", 
                        help="Video player to use (default: mpv)")
    parser.add_argument("--audio-only", action="store_true", help="Play audio only")
    parser.add_argument("--fullscreen", action="store_true", help="Play video in fullscreen mode", default=True)
    parser.add_argument("--vertical", action="store_true", help="Optimize for vertical/portrait display")
    parser.add_argument("--stretch", action="store_true", help="Stretch video to fill screen")
    parser.add_argument("--crop", help="Crop video (format: w:h:x:y)", default=None)
    parser.add_argument("--zoom", type=float, help="Zoom factor for video (e.g., 1.5)", default=None)
    parser.add_argument("--center-cut", action="store_true", help="Center cut the video to fill vertical screen")
    parser.add_argument("--vertical-1080", action="store_true", help="Optimize for 1080x1920 vertical display")
    parser.add_argument("--max-quality", action="store_true", help="Play at maximum available resolution", default=False)
    parser.add_argument("--quality", type=str, choices=["best", "1080p", "720p", "480p", "360p"], 
                       help="Specific quality to play (default: best)", default="best")
    return parser.parse_args()

def is_valid_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube URL."""
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return bool(re.match(youtube_regex, url))

def play_with_mpv(url: str, audio_only: bool = False, fullscreen: bool = True, vertical: bool = False, 
                 stretch: bool = False, crop: str = None, zoom: float = None, center_cut: bool = False,
                 vertical_1080: bool = False, max_quality: bool = False, quality: str = "best") -> None:
    """Play YouTube URL using mpv player."""
    command = ["mpv"]
    if audio_only:
        command.append("--audio-only")
    if fullscreen:
        command.append("--fullscreen")
    
    # Quality settings
    if max_quality or quality == "best":
        command.extend(["--ytdl-format=bestvideo+bestaudio/best"])
    elif quality == "1080p":
        command.extend(["--ytdl-format=bestvideo[height<=1080]+bestaudio/best[height<=1080]"])
    elif quality == "720p":
        command.extend(["--ytdl-format=bestvideo[height<=720]+bestaudio/best[height<=720]"])
    elif quality == "480p":
        command.extend(["--ytdl-format=bestvideo[height<=480]+bestaudio/best[height<=480]"])
    elif quality == "360p":
        command.extend(["--ytdl-format=bestvideo[height<=360]+bestaudio/best[height<=360]"])
    
    # Handle vertical/portrait display
    if vertical:
        # Rotate video 90 degrees
        command.extend(["--video-rotate=90"])
    
    # Handle stretch to fill
    if stretch:
        command.extend(["--panscan=1.0"])
        command.extend(["--no-keepaspect"])
    
    # Handle custom crop
    if crop:
        command.extend(["--vf=crop=" + crop])
    
    # Handle zoom
    if zoom:
        command.extend([f"--vf=lavfi=[scale=iw*{zoom}:ih*{zoom}]"])
    
    # Center cut (good for vertical displays)
    if center_cut:
        command.extend(["--vf=lavfi=[crop=iw/2:ih:iw/4:0]"])
    
    # Specific optimization for 1080x1920 vertical display
    if vertical_1080:
        # Create a filter that will:
        # 1. Crop the center of the video to match vertical aspect ratio
        # 2. Scale it to exactly fill 1080x1920 with no padding
        command.extend(["--vf=lavfi=[crop=ih*9/16:ih:iw/2-ih*9/32:0,scale=1080:1920,setdar=9/16]"])
        command.extend(["--no-keepaspect"])  # Force filling the screen
    
    command.append(url)
    subprocess.run(command)

def play_with_vlc(url: str, audio_only: bool = False, fullscreen: bool = True, vertical: bool = False, 
                 stretch: bool = False, crop: str = None, zoom: float = None, center_cut: bool = False,
                 vertical_1080: bool = False, max_quality: bool = False, quality: str = "best") -> None:
    """Play YouTube URL using VLC player."""
    command = ["vlc"]
    if audio_only:
        command.extend(["--no-video"])
    if fullscreen:
        command.extend(["--fullscreen"])
    
    # Handle vertical/portrait display
    if vertical:
        command.extend(["--video-filter=transform", "--transform-type=90"])
    
    # Handle stretch to fill
    if stretch:
        command.extend(["--aspect-ratio=0:0"])  # This disables aspect ratio preservation
    
    # Specific optimization for 1080x1920 vertical display
    if vertical_1080:
        command.extend(["--aspect-ratio=0:0"])  # Force fill
        command.extend(["--crop=9:16"])  # Crop to vertical aspect ratio
    
    # Handle custom crop
    if crop:
        command.extend(["--vf=crop=" + crop])
    
    # Handle zoom
    if zoom:
        command.extend([f"--vf=lavfi=[scale=iw*{zoom}:ih*{zoom}]"])
    
    # Center cut (good for vertical displays)
    if center_cut:
        command.extend(["--vf=lavfi=[crop=iw/2:ih:iw/4:0]"])
    
    command.append(url)
    subprocess.run(command)

def play_with_omxplayer(url: str, audio_only: bool = False, fullscreen: bool = True, vertical: bool = False, 
                       stretch: bool = False, crop: str = None, zoom: float = None, center_cut: bool = False,
                       vertical_1080: bool = False, max_quality: bool = False, quality: str = "best") -> None:
    """Play YouTube URL using omxplayer (legacy Raspberry Pi player)."""
    # First extract the direct stream URL using youtube-dl
    result = subprocess.run(
        ["youtube-dl", "-g", url],
        capture_output=True,
        text=True
    )
    stream_url = result.stdout.strip()
    
    command = ["omxplayer"]
    if audio_only:
        command.append("-o")
        command.append("local")
    # omxplayer is fullscreen by default, but can be explicitly set
    if fullscreen:
        command.append("-r")  # Force fullscreen
    
    # Handle stretch to fill (omxplayer has limited options for this)
    if stretch:
        command.append("--stretch")
    
    # Note: omxplayer doesn't have great rotation support
    # For vertical displays, we'll rely on stretching
    
    # Add vertical_1080 handling for omxplayer
    if vertical_1080:
        command.append("--stretch")  # Force stretch to fill
    
    command.append(stream_url)
    subprocess.run(command)

def get_player_strategies() -> Dict[str, Callable]:
    """Return a dictionary of player strategy functions."""
    return {
        "mpv": play_with_mpv,
        "vlc": play_with_vlc,
        "omxplayer": play_with_omxplayer
    }

def play_youtube(url: str, player: str = "mpv", audio_only: bool = False, fullscreen: bool = True, 
                vertical: bool = False, stretch: bool = False, crop: str = None, zoom: float = None, 
                center_cut: bool = False, vertical_1080: bool = False, max_quality: bool = False,
                quality: str = "best") -> None:
    """
    Play YouTube video using specified player.
    
    Args:
        url: YouTube URL to play
        player: Video player to use (default: mpv)
        audio_only: Whether to play only audio (default: False)
        fullscreen: Whether to play in fullscreen mode (default: True)
        vertical: Whether to optimize for vertical display (default: False)
        stretch: Whether to stretch video to fill screen (default: False)
        crop: Crop video (format: w:h:x:y)
        zoom: Zoom factor for video (e.g., 1.5)
        center_cut: Whether to center cut the video to fill vertical screen
        vertical_1080: Whether to optimize for 1080x1920 vertical display
        max_quality: Whether to play at maximum available resolution
        quality: Specific quality to play (default: best)
    """
    if not is_valid_youtube_url(url):
        print(f"Invalid YouTube URL: {url}")
        return
    
    strategies = get_player_strategies()
    if player not in strategies:
        print(f"Unknown player: {player}. Using mpv.")
        player = "mpv"
    
    strategies[player](url, audio_only, fullscreen, vertical, stretch, crop, zoom, center_cut, vertical_1080, max_quality, quality)

def main() -> None:
    """Main function to parse arguments and play YouTube video."""
    args = parse_arguments()
    
    if args.url:
        play_youtube(args.url, args.player, args.audio_only, args.fullscreen, 
                    args.vertical, args.stretch, args.crop, args.zoom, args.center_cut,
                    args.vertical_1080, args.max_quality, args.quality)
    else:
        url = input("Enter YouTube URL: ")
        play_youtube(url, args.player, args.audio_only, args.fullscreen, 
                   args.vertical, args.stretch, args.crop, args.zoom, args.center_cut,
                   args.vertical_1080, args.max_quality, args.quality)

def play_video(url):
    script = " python3 tools/youtube_player.py --url " + url + " --vertical-1080 --max-quality"
    os.system(script)

if __name__ == "__main__":
    main() 