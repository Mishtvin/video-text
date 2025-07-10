"""
FFmpeg downloader and manager for automatic installation.
"""

import os
import sys
import platform
import zipfile
import tarfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import urllib.request
from urllib.error import URLError

from utils.logger import get_logger
from utils.config import get_app_data_dir

class FFmpegManager:
    """Manage FFmpeg installation and usage."""
    
    def __init__(self):
        self.logger = get_logger()
        self.app_data_dir = get_app_data_dir()
        self.ffmpeg_dir = os.path.join(self.app_data_dir, "ffmpeg")
        self.ffmpeg_executable = self._get_ffmpeg_executable_path()
        
    def _get_ffmpeg_executable_path(self) -> str:
        """Get the path to FFmpeg executable."""
        if platform.system() == "Windows":
            return os.path.join(self.ffmpeg_dir, "bin", "ffmpeg.exe")
        else:
            return os.path.join(self.ffmpeg_dir, "bin", "ffmpeg")
    
    def _get_download_info(self) -> Optional[dict]:
        """Get download information for current platform."""
        system = platform.system()
        machine = platform.machine()
        
        # FFmpeg static builds URLs
        base_url = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/"
        
        if system == "Windows":
            if machine.lower() in ['amd64', 'x86_64']:
                return {
                    'url': f"{base_url}ffmpeg-master-latest-win64-gpl.zip",
                    'format': 'zip',
                    'extract_dir': 'ffmpeg-master-latest-win64-gpl'
                }
        elif system == "Linux":
            if machine.lower() in ['x86_64', 'amd64']:
                return {
                    'url': f"{base_url}ffmpeg-master-latest-linux64-gpl.tar.xz",
                    'format': 'tar',
                    'extract_dir': 'ffmpeg-master-latest-linux64-gpl'
                }
        elif system == "Darwin":  # macOS
            return {
                'url': f"{base_url}ffmpeg-master-latest-macos64-gpl.zip",
                'format': 'zip',
                'extract_dir': 'ffmpeg-master-latest-macos64-gpl'
            }
        
        return None
    
    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available (system or bundled)."""
        # Check bundled FFmpeg first
        if os.path.exists(self.ffmpeg_executable):
            try:
                result = subprocess.run(
                    [self.ffmpeg_executable, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self.logger.info("Using bundled FFmpeg")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # Check system FFmpeg
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.info("Using system FFmpeg")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    
    def get_ffmpeg_path(self) -> str:
        """Get the path to FFmpeg executable to use."""
        # Try bundled FFmpeg first
        if os.path.exists(self.ffmpeg_executable):
            return self.ffmpeg_executable
        
        # Fall back to system FFmpeg
        return "ffmpeg"
    
    def download_ffmpeg(self, progress_callback=None) -> bool:
        """Download and install FFmpeg."""
        download_info = self._get_download_info()
        if not download_info:
            self.logger.error("FFmpeg download not supported for this platform")
            return False
        
        try:
            # Create directories
            os.makedirs(self.ffmpeg_dir, exist_ok=True)
            temp_dir = os.path.join(self.ffmpeg_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download file
            download_url = download_info['url']
            filename = os.path.basename(download_url)
            download_path = os.path.join(temp_dir, filename)
            
            self.logger.info(f"Downloading FFmpeg from: {download_url}")
            
            if progress_callback:
                progress_callback(0, "Starting download...")
            
            def progress_hook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    percentage = min(int(downloaded * 100 / total_size), 100)
                    progress_callback(percentage, f"Downloading... {percentage}%")
            
            urllib.request.urlretrieve(download_url, download_path, progress_hook)
            
            if progress_callback:
                progress_callback(90, "Extracting...")
            
            # Extract archive
            extract_path = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_path, exist_ok=True)
            
            if download_info['format'] == 'zip':
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
            elif download_info['format'] == 'tar':
                with tarfile.open(download_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(extract_path)
            
            # Move extracted files
            extracted_dir = os.path.join(extract_path, download_info['extract_dir'])
            if os.path.exists(extracted_dir):
                # Copy bin directory
                src_bin = os.path.join(extracted_dir, "bin")
                dst_bin = os.path.join(self.ffmpeg_dir, "bin")
                
                if os.path.exists(src_bin):
                    if os.path.exists(dst_bin):
                        shutil.rmtree(dst_bin)
                    shutil.copytree(src_bin, dst_bin)
                
                # Make executable on Unix systems
                if platform.system() != "Windows":
                    ffmpeg_path = os.path.join(dst_bin, "ffmpeg")
                    if os.path.exists(ffmpeg_path):
                        os.chmod(ffmpeg_path, 0o755)
            
            # Clean up temp files
            shutil.rmtree(temp_dir)
            
            if progress_callback:
                progress_callback(100, "Installation complete!")
            
            # Verify installation
            if os.path.exists(self.ffmpeg_executable):
                self.logger.info("FFmpeg downloaded and installed successfully")
                return True
            else:
                self.logger.error("FFmpeg installation verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"FFmpeg download failed: {str(e)}")
            # Clean up on failure
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
            return False
    
    def ensure_ffmpeg(self, progress_callback=None) -> bool:
        """Ensure FFmpeg is available, download if necessary."""
        if self.is_ffmpeg_available():
            return True
        
        self.logger.info("FFmpeg not found, attempting to download...")
        return self.download_ffmpeg(progress_callback)
    
    def get_version_info(self) -> Optional[str]:
        """Get FFmpeg version information."""
        try:
            ffmpeg_path = self.get_ffmpeg_path()
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.split('\n')[0]
                return first_line
        except:
            pass
        return None