import argparse
import logging
import os
import sys
from os.path import exists, basename
import pyexiv2


def validate_inputs(photo_path, video_path):
    """
    Checks if the files provided are valid inputs. Currently the only supported inputs are MP4/MOV and JPEG filetypes.
    Currently it only checks file extensions instead of actually checking file formats via file signature bytes.
    :param photo_path: path to the photo file
    :param video_path: path to the video file
    :return: True if photo and video files are valid, else False
    """
    if not exists(photo_path):
        logging.error("Photo does not exist: {}".format(photo_path))
    if not exists(video_path):
        logging.error("Video does not exist: {}".format(video_path))
    if not photo_path.lower().endswith(('.jpg', '.jpeg')):
        logging.error("Photo isn't a JPEG: {}".format(photo_path))
    if not video_path.lower().endswith(('.mov', '.mp4')):
        logging.error("Video isn't a MOV or MP4: {}".format(photo_path))


def merge_files(photo_path, video_path):
    """Merges the photo and video file together by concatenating the video at the end of the photo. Writes the output to
    a temporary folder.
    :param photo_path: Path to the photo
    :param video_path: Path to the video
    :return: File name of the merged output file
    """
    logging.info("Merging {} and {}.".format(photo_path, video_path))
    out_path = "output/{}".format(basename(photo_path))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as outfile, open(photo_path, "rb") as photo, open(video_path, "rb") as video:
        outfile.write(photo.read())
        outfile.write(video.read())
    logging.info("Merged photo and video.")
    return out_path


def add_xmp_metadata(merged_file, offset):
    """Adds XMP metadata to the merged image indicating the byte offset in the file where the video begins.
    :param merged_file: The path to the file that has the photo and video merged together.
    :param offset: The number of bytes from EOF to the beginning of the video.
    :return: None
    """
    metadata = pyexiv2.ImageMetadata(merged_file)
    logging.info("Reading existing metadata from file.")
    metadata.read()
    logging.info("Found XMP keys: " + str(metadata.xmp_keys))
    if len(metadata.xmp_keys) > 0:
        logging.warning("Found existing XMP keys. They *may* be affected after this process.")
    pyexiv2.xmp.register_namespace('http://ns.google.com/photos/1.0/camera/', 'GCamera')
    metadata['Xmp.GCamera.MicroVideo'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideo', 1)
    metadata['Xmp.GCamera.MicroVideoVersion'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideoVersion', 1)
    metadata['Xmp.GCamera.MicroVideoOffset'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideoOffset', offset)
    metadata['Xmp.GCamera.MicroVideoPresentationTimestampUs'] = pyexiv2.XmpTag(
        'Xmp.GCamera.MicroVideoPresentationTimestampUs',
        10)  # Not really sure what this field means, but this was the value in a reference image I found.
    metadata.write()


def main(args):
    logging_level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=logging_level, stream=sys.stdout)
    photo_path = args.photo
    video_path = args.video
    validate_inputs(photo_path, video_path)

    merged = merge_files(photo_path, video_path)
    photo_filesize = os.path.getsize(photo_path)
    merged_filesize = os.path.getsize(merged)

    # The 'offset' field in the XMP metadata should be the offset (in bytes) from the end of the file to the part
    # where the video portion of the merged file begins. In other words, merged size - photo_only_size = offset.
    offset = merged_filesize - photo_filesize
    add_xmp_metadata(merged, offset)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merges a photo and video into a Microvideo-formatted Google Motion Photo')
    parser.add_argument('--verbose', help='Show logging messages', action='store_true')
    parser.add_argument('--photo', type=str, help='Path to the JPEG photo to add.')
    parser.add_argument('--video', type=str, help='Path to the MOV video to add.')
    main(parser.parse_args())
