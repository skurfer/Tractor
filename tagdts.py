#!/usr/bin/env python3
"""
Take a collection of naked DTS, WAV, or AC3 files and
embed them inside an MKA container with metadata.

The filesystem layout is assumed to be:

    Artist - Album/01 - Track Name.dts

"""
import os
import sys
import re
import subprocess
import argparse
from mimetypes import guess_type


def quoted(arg):
    arg = arg.replace("'", r"\'")
    if ' ' in arg:
        arg = "'{}'".format(arg)
    return arg


def scan_args():
    """get command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n', '--dry-run',
        help="show the commands that will be run, but do nothing",
        action='store_true',
    )
    parser.add_argument(
        '--genre',
        help="the musical genre",
    )
    parser.add_argument(
        '--date',
        help="the release date",
    )
    parser.add_argument(
        '-a',
        '--artwork', help="path to a cover image (PNG or JPEG)",
    )
    parser.add_argument(
        '--disc',
        help='disc number',
    )
    parser.add_argument(
        'source_path',
        nargs=1,
    )
    return parser.parse_args()


def source_info(source_path):
    dir_name = os.path.basename(source_path)
    return dir_name.split(' - ')


def track_info(file_name):
    cap = re.match('(\d+)\s-\s(.+)\.(?:ac3|dts|wav)', file_name)
    if cap is None:
        return (None, None)
    return (
        cap.group(1),
        cap.group(2),
    )


def tag_command(track_path, metadata, dest_dir, artwork=None):
    tag_cmd = ['ffmpeg', '-i', track_path, '-c:a', 'copy']
    for key, val in metadata.items():
        if key in ('track', 'disc'):
            # kill leading zeros
            val = val.lstrip('0')
        tag_cmd.extend(['-metadata', key + '=' + val])
    if artwork:
        img_type = guess_type(artwork)
        tag_cmd.extend([
            '-attach',
            artwork,
            '-metadata:s:1',
            'mimetype=' + img_type[0],
        ])
    out_file = '{}{}{track} - {title}.mka'.format(
        dest_dir,
        os.path.sep,
        **metadata,
    )
    tag_cmd.append(out_file)
    return tag_cmd

args = scan_args()
source_path = args.source_path[0]
artist, album = source_info(source_path)
metadata = {
    'artist': artist,
    'album': album,
}
if args.date:
    metadata['date_released'] = args.date
if args.genre:
    metadata['genre'] = args.genre
if args.artwork and not os.path.exists(args.artwork):
    print('WARNING: Image not found at ' + args.artwork)
    args.artwork = None

track_files = os.listdir(source_path)
for tf in track_files:
    track, title = track_info(tf)
    if track is None:
        continue
    metadata['track'] = track
    metadata['title'] = title
    track_path = os.path.sep.join([source_path, tf])
    cmd = tag_command(track_path, metadata, source_path, args.artwork)
    if args.dry_run:
        print(' '.join([quoted(arg) for arg in cmd]))
    else:
        print('Processing {} {}'.format(track, title))
        subprocess.call(
            cmd,
            stderr=subprocess.DEVNULL,
        )
