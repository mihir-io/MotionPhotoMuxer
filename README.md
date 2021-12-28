MotionPhotoMuxer
================

Convert Apple Live Photos into Google Motion Photos.

# Installation

As of right now, this script only has one dependency, `py3exiv2`. Unfortunately
this requires building a C++ library to install, so you need to install a C++ toolchain.

Using Ubuntu as an example:

~~~bash
sudo apt-get install build-essential python-all-dev libexiv2-dev libboost-python-dev python3 python3-venv
python3 -m pip install -r requirements.txt
~~~

# Usage

~~~
python MotionPhotoMuxer.py
usage: MotionPhotoMuxer.py [-h] [--verbose] [--photo PHOTO] [--video VIDEO]

Merges a photo and video into a Microvideo-formatted Google Motion Photo

optional arguments:
  -h, --help     show this help message and exit
  --verbose      Show logging messages
  --photo PHOTO  Path to the JPEG photo to add.
  --video VIDEO  Path to the MOV video to add.
~~~

A JPEG photo and MOV or MP4 video must be provided. The code only does simple
error checking to see if the file extensions are `.jpg|.jpeg` and `.mov|.mp4`
respectively, so if the actual photo/video encoding is something funky, things
may not work right.

This has been tested successfully on a couple photos taken on an iPhone 12 and
uploaded to Google Photos through a Pixel XL, but there hasn't been any
extensive testing done yet, so use at your own risk!

# Credit

This wouldn't have been possible without the excellent writeup on the process
of working with Motion Photos [here](https://medium.com/android-news/working-with-motion-photos-da0aa49b50c).