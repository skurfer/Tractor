#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import argparse
from mimetypes import guess_type


layout_formats = {
    'plex': {
        'track': '{track:02d} - {title}.{0}',
        'album': '{} - {}',
    },
    'itunes': {
        'track': '{track:02d} {title}.{0}',
        'album': os.path.join('{}', '{}'),
    },
}


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
        help='show the commands that will be run, but do nothing',
        action='store_true',
    )
    parser.add_argument(
        '-s',
        '--source', help='path to the source file',
    )
    parser.add_argument(
        '-d',
        '--metadata', help='path to a CUE or JSON file containing metadata',
        default='',
    )
    parser.add_argument(
        '-a',
        '--artwork', help='path to a cover image (PNG or JPEG)',
    )
    parser.add_argument(
        '-c', '--container',
        help='put the data into a container with metadata',
        action='store_true',
    )
    parser.add_argument(
        '--disc',
        help='disc number',
    )
    parser.add_argument(
        '-l', '--layout',
        help='file system layout style',
        choices=layout_formats.keys(),
        default='plex',
    )
    parser.add_argument(
        '--stream',
        help='force extraction from a specific stream',
        default=1,
    )
    return parser.parse_args()


def md_from_cue(cue_path):
    """read metadata from a CUE file"""
    cue_data = {'audio_codec': 'dts'}
    tracks = []
    with open(cue_path) as cue_file:
        for line in cue_file:
            line = line.rstrip()
            if line.startswith('REM GENRE '):
                cue_data['genre'] = ' '.join(
                    line.split(' ')[2:]
                ).strip('"')
            if line.startswith('REM DATE '):
                cue_data['date_released'] = ' '.join(
                    line.split(' ')[2:]
                ).strip('"')
            if line.startswith('REM DISCNUMBER '):
                cue_data['disc'] = ' '.join(
                    line.split(' ')[2:]
                ).strip('"')
            if line.startswith('PERFORMER '):
                cue_data['artist'] = ' '.join(
                    line.split(' ')[1:]
                ).replace('"', '')
            if line.startswith('TITLE '):
                cue_data['album'] = ' '.join(
                    line.split(' ')[1:]
                ).replace('"', '')
            if line.startswith('FILE '):
                cue_data['media_source'] = ' '.join(
                    line.split(' ')[1:-1]
                ).replace('"', '')

            if line.startswith('  TRACK '):
                track = {}
                track['track'] = int(line.strip().split(' ')[1], 10)

                tracks.append(track)

            if line.startswith('    TITLE '):
                tracks[-1]['title'] = ' '.join(
                    line.strip().split(' ')[1:]
                ).replace('"', '')
            if line.startswith('    PERFORMER '):
                tracks[-1]['artist'] = ' '.join(
                    line.strip().split(' ')[1:]
                ).replace('"', '')
            if line.startswith('    INDEX 01 '):
                t = list(map(int, ' '.join(
                    line.strip().split(' ')[2:]
                ).replace('"', '').split(':')))
                tracks[-1]['start'] = float(t[0] * 60 + t[1] + t[2]/60.0)
                tracks[-1]['duration'] = None
        cue_data['tracks'] = tracks
        return cue_data


def md_from_json(json_path):
    """read metadata from a JSON file"""
    data = {}
    with open(json_path) as json_file:
        data = json.load(json_file)
    return data


def md_from_ffprobe(source_path):
    """read metadata from source media using ffprobe"""
    probe_cmd = [
        'ffprobe', '-hide_banner',
        '-show_streams', '-show_chapters',
        '-print_format', 'json',
        source_path,
    ]
    text_data = subprocess.check_output(
        probe_cmd,
        stderr=subprocess.DEVNULL,
    ).decode('utf-8')
    ffprobe_data = json.loads(text_data)
    # find audio stream and format
    audio_codec = 'dts'
    data = {}
    streams = ffprobe_data.get('streams', [])
    global force_stream
    if len(streams) == 1:
        # proably audio data with no container
        force_stream = 0
    for stream in streams:
        if stream['codec_type'] != 'audio':
            continue
        if force_stream and stream['index'] != force_stream:
            continue
        data['stream_index'] = stream['index']
        codec = stream['codec_long_name']
        if 'AC-3' in codec:
            audio_codec = 'ac3'
        if 'PCM' in codec:
            audio_codec = 'wav'
            if container and stream['channels'] == 2:
                audio_codec = 'alac'
        if codec.startswith('MLP'):
            audio_codec = 'mlp'
    data['audio_codec'] = audio_codec
    tracks = []
    for (track, chapter) in enumerate(ffprobe_data['chapters'], 1):
        title = chapter['tags']['title']
        start = float(chapter['start_time'])
        end = float(chapter['end_time'])
        tracks.append({
            'track': track,
            'title': title,
            'start': start,
            'duration': end - start,
        })
    data['tracks'] = tracks
    return data


def add_duration(data):
    """use start times to determine durations"""
    if 'tracks' not in data:
        return data
    tracks = data['tracks']
    if not all(['start' in t for t in tracks]):
        return data
    for i, track in enumerate(tracks):
        if i != len(tracks) - 1:
            nextt = tracks[i + 1]
            track['duration'] = nextt['start'] - track['start']
            data['tracks'][i] = track
    if not data['tracks'][-1].get('duration'):
        data['tracks'][-1]['duration'] = None
    return data


def scan_metadata(source_path, md_path):
    """find and merge metadata"""
    data = {
        'media_source': source_path,
        'stream_index': 0,
    }
    md_base, md_ext = os.path.splitext(md_path)
    if md_ext.lower() == '.cue':
        data = {**data, **md_from_cue(md_path)}
    else:
        data = {**data, **md_from_ffprobe(source_path)}
    if md_ext.lower() == '.json':
        data = {**data, **md_from_json(md_path)}
    # fall back values for album/artist
    if 'artist' not in data and ' - ' in source_path:
        data['artist'] = source_path.split(' - ')[0]
    if 'album' not in data and ' - ' in source_path:
        last_part = source_path.split(' - ')[1]
        data['album'] = os.path.splitext(last_part)[0]
    data = add_duration(data)
    return data


def output_formats(codec, container):
    """determine codec and file extension"""
    file_extension = codec
    if container:
        if codec == 'alac':
            file_extension = 'm4a'
        else:
            file_extension = 'mka'
    return (codec, file_extension)


def make_destination(dest_path):
    if os.path.exists(dest_path):
        if not os.path.isdir(dest_path):
            print("Destination folder '{}' can't be created".format(dest_path))
            sys.exit(74)
    else:
        os.makedirs(dest_path)


def ffmpeg_cmds(album_dir, track_fmt, metadata, container, cover_art):
    """generate a list of ffmpeg commands for each track"""
    ffmpeg_cmd_base = [
        'ffmpeg',
        # source file
        '-i', metadata['media_source'],
        # discard video
        '-map', '0:' + str(metadata['stream_index']),
        # audio codec
        '-c:a', 'alac' if metadata['audio_codec'] == 'alac' else 'copy',
        # metadata (optional - added later)
        # filename (added later)
    ]
    for t in metadata['tracks']:
        ffmpeg_cmd = ffmpeg_cmd_base[:]
        ffmpeg_cmd.extend(['-ss', '{start:.3f}'.format(**t)])
        if t['duration']:
            ffmpeg_cmd.extend(['-t', '{duration:.3f}'.format(**t)])
        # if metadata['audio_codec'] == 'alac':
        #     ffmpeg_cmd[6] = 'alac'
        filename = track_fmt.format(metadata['file_extension'], **t)
        if container:
            track = t['track']
            title = t['title']
            ffmpeg_cmd.extend(['-metadata', 'track=' + str(track)])
            ffmpeg_cmd.extend(['-metadata', 'title=' + title])
            for field in (
                'genre',
                'artist',
                'album',
                'composer',
                'date_released',
                'disc'
            ):
                if field in metadata:
                    kv = '{}={}'.format(field, metadata[field])
                    ffmpeg_cmd.extend(['-metadata', kv])
                    if field == 'disc':
                        disc = metadata[field].split('/')[0]
                        filename = '{}-{}'.format(disc, filename)
            if cover_art and os.path.exists(cover_art):
                img_type = guess_type(cover_art)
                ffmpeg_cmd.extend([
                    '-attach',
                    cover_art,
                    '-metadata:s:1',
                    'mimetype=' + img_type[0],
                ])
        out_path = os.path.join(album_dir, filename)
        ffmpeg_cmd.append(out_path)
        yield ffmpeg_cmd


args = scan_args()

source_path = args.source
md_path = args.metadata
if source_path is None and md_path is None:
    print('Please provide either a source or metadata file')
    sys.exit(66)
cover_art = args.artwork
force_stream = int(args.stream)
container = args.container
dry_run = args.dry_run
track_fmt = layout_formats[args.layout]['track']
# default output directory
if source_path:
    album_dir = os.path.splitext(source_path)[0]
else:
    album_dir = os.path.splitext(md_path)[0]
album_fmt = layout_formats[args.layout]['album']

metadata = scan_metadata(source_path, md_path)
album_dir = album_fmt.format(metadata['artist'], metadata['album'])
(ac, ext) = output_formats(
    metadata['audio_codec'],
    container,
)
metadata['audio_codec'] = ac
metadata['file_extension'] = ext
if args.disc:
    metadata['disc'] = args.disc.lstrip('0')
if container and cover_art and ext != 'mka':
    print('WARNING: Cover art is only supported in '
          'Matroska containers. Ignoring.')
commands = ffmpeg_cmds(album_dir, track_fmt, metadata, container, cover_art)

if not dry_run:
    make_destination(album_dir)
for track_no, cmd in enumerate(commands, 1):
    if dry_run:
        print(' '.join([quoted(arg) for arg in cmd]))
        continue
    print('Processing track ' + str(track_no))
    subprocess.call(cmd, stderr=subprocess.DEVNULL)
