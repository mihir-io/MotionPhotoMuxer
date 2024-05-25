import argparse
import logging
import shutil
import sys
from pathlib import Path

import pyexiv2

def validate_directory(dir: Path):
    
    if not dir.exists():
        logging.error("Path doesn't exist: {}".format(dir))
        exit(1)
    if not dir.is_dir():
        logging.error("Path is not a directory: {}".format(dir))
        exit(1)

def validate_media(photo_path: Path, video_path: Path):
    """
    Checks if the files provided are valid inputs. Currently the only supported inputs are MP4/MOV and JPEG filetypes.
    Currently it only checks file extensions instead of actually checking file formats via file signature bytes.
    :param photo_path: path to the photo file
    :param video_path: path to the video file
    :return: True if photo and video files are valid, else False
    """
    if not photo_path.exists():
        logging.error("Photo does not exist: {}".format(photo_path))
        return False
    if not video_path.exists():
        logging.error("Video does not exist: {}".format(video_path))
        return False
    if not photo_path.suffix.lower() in ['.jpg', '.jpeg']:
        logging.error("Photo isn't a JPEG: {}".format(photo_path))
        return False
    if not video_path.suffix.lower() in ['.mov', '.mp4']:
        logging.error("Video isn't a MOV or MP4: {}".format(photo_path))
        return False
    return True

def merge_files(photo_path: Path, video_path: Path, output_path: Path) -> Path:
    """Merges the photo and video file together by concatenating the video at the end of the photo. Writes the output to
    a temporary folder.
    :param photo_path: Path to the photo
    :param video_path: Path to the video
    :return: File name of the merged output file
    """
    logging.info("Merging {} and {}.".format(photo_path, video_path))
    out_path = output_path / photo_path.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as outfile, open(photo_path, "rb") as photo, open(video_path, "rb") as video:
        outfile.write(photo.read())
        outfile.write(video.read())
    logging.info("Merged photo and video.")
    return out_path


def add_xmp_metadata(merged_file: Path, offset: int):
    """Adds XMP metadata to the merged image indicating the byte offset in the file where the video begins.
    :param merged_file: The path to the file that has the photo and video merged together.
    :param offset: The number of bytes from EOF to the beginning of the video.
    :return: None
    """
    metadata = pyexiv2.ImageMetadata(str(merged_file.resolve()))
    logging.info("Reading existing metadata from file.")
    metadata.read()
    logging.info("Found XMP keys: " + str(metadata.xmp_keys))
    if len(metadata.xmp_keys) > 0:
        logging.warning("Found existing XMP keys. They *may* be affected after this process.")

    # (py)exiv2 raises an exception here on basically all my 'test' iPhone 13 photos -- I'm not sure why,
    # but it seems safe to ignore so far. It's logged anyways just in case.
    try:
        pyexiv2.xmp.register_namespace('http://ns.google.com/photos/1.0/camera/', 'GCamera')
    except KeyError:
        logging.warning("exiv2 detected that the GCamera namespace already exists.".format(merged_file))
    metadata['Xmp.GCamera.MicroVideo'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideo', 1)
    metadata['Xmp.GCamera.MicroVideoVersion'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideoVersion', 1)
    metadata['Xmp.GCamera.MicroVideoOffset'] = pyexiv2.XmpTag('Xmp.GCamera.MicroVideoOffset', offset)
    metadata['Xmp.GCamera.MicroVideoPresentationTimestampUs'] = pyexiv2.XmpTag(
        'Xmp.GCamera.MicroVideoPresentationTimestampUs',
        1500000)  # in Apple Live Photos, the chosen photo is 1.5s after the start of the video, so 1500000 microseconds
    metadata.write()


def convert(photo_path: Path, video_path: Path, output_path: Path):
    """
    Performs the conversion process to mux the files together into a Google Motion Photo.
    :param photo_path: path to the photo to merge
    :param video_path: path to the video to merge
    :return: True if conversion was successful, else False
    """
    merged = merge_files(photo_path, video_path, output_path)
    photo_filesize = photo_path.stat().st_size
    merged_filesize = merged.stat().st_size

    # The 'offset' field in the XMP metadata should be the offset (in bytes) from the end of the file to the part
    # where the video portion of the merged file begins. In other words, merged size - photo_only_size = offset.
    offset = merged_filesize - photo_filesize
    add_xmp_metadata(merged, offset)

def matching_video(photo_path: Path) -> Path:
    base = photo_path.stem
    logging.info(f"Looking for videos named: {base}")
    video_extensions = ['.mov', '.mp4', '.MOV', '.MP4']
    for ext in video_extensions:
        video_path = photo_path.with_suffix(ext)
        if video_path.exists():
            return video_path
    return Path("")


def process_directory(file_dir: Path, recurse: bool):
    """
    Loops through files in the specified directory and generates a list of (photo, video) path tuples that can
    be converted
    :TODO: Implement recursive scan
    :param file_dir: directory to look for photos/videos to convert
    :param recurse: if true, subdirectories will recursively be processes
    :return: a list of tuples containing matched photo/video pairs.
    """
    logging.info("Processing dir: {}".format(file_dir))
    if recurse:
        logging.error("Recursive traversal is not implemented yet.")
        exit(1)

    file_pairs = []
    for file in file_dir.iterdir():
        if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg'] and matching_video(file) != Path(""):
            file_pairs.append((file, matching_video(file)))

    logging.info("Found {} pairs.".format(len(file_pairs)))
    logging.info("subset of found image/video pairs: {}".format(str(file_pairs[0:9])))
    return file_pairs


def main(args):
    logging_level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=logging_level, stream=sys.stdout)
    logging.info("Enabled verbose logging")

    outdir = args.output if args.output is not None else Path("output")

    if args.dir is not None:
        validate_directory(args.dir)
        pairs = process_directory(args.dir, args.recurse)
        procesed_files = set()
        for pair in pairs:
            if validate_media(pair[0], pair[1]):
                convert(pair[0], pair[1], outdir)
                procesed_files.add(pair[0])
                procesed_files.add(pair[1])

        if args.copyall:
            # Copy the remaining files to outdir
            all_files = set(file for file in args.dir.iterdir())
            remaining_files = all_files - procesed_files

            logging.info("Found {} remaining files that will copied.".format(len(remaining_files)))

            if len(remaining_files) > 0:
                # Ensure the destination directory exists
                outdir.mkdir(parents=True, exist_ok=True)
                
                for file in remaining_files:
                    file_name = file.name
                    destination_path = outdir / file_name
                    shutil.copy2(file, destination_path)
    else:
        if args.photo is None and args.video is None:
            logging.error("Either --dir or --photo and --video are required.")
            exit(1)

        if bool(args.photo) ^ bool(args.video):
            logging.error("Both --photo and --video must be provided.")
            exit(1)

        if validate_media(args.photo, args.video):
            convert(args.photo, args.video, outdir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merges a photo and video into a Microvideo-formatted Google Motion Photo')
    parser.add_argument('--verbose', help='Show logging messages.', action='store_true')
    parser.add_argument('--dir', type=Path, help='Process a directory for photos/videos. Takes precedence over '
                                                '--photo/--video')
    parser.add_argument('--recurse', help='Recursively process a directory. Only applies if --dir is also provided',
                        action='store_true')
    parser.add_argument('--photo', type=Path, help='Path to the JPEG photo to add.')
    parser.add_argument('--video', type=Path, help='Path to the MOV video to add.')
    parser.add_argument('--output', type=Path, help='Path to where files should be written out to.')
    parser.add_argument('--copyall', help='Copy unpaired files to directory.', action='store_true')

    main(parser.parse_args())
