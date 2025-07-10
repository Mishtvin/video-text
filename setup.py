"""
Setup script for Video Transcriber application.
"""

from setuptools import setup, find_packages

setup(
    name="video-transcriber",
    version="1.0.0",
    author="Video Transcriber Team",
    description="Offline Video Transcriber & Searcher - Desktop application for video transcription and searchable subtitle generation",
    packages=find_packages(include=['core', 'gui', 'modules', 'utils']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=[
        "PySide6>=6.5.0",
        "openai-whisper>=20231117",
        "ffmpeg-python>=0.2.0",
        "pysubs2>=1.6.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "video-transcriber=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
