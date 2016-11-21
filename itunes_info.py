#!/usr/bin/python
from ScriptingBridge import SBApplication, NSPredicate


iTunes = SBApplication.applicationWithBundleIdentifier_('com.apple.iTunes')

metadata = {
    'date_released': '2007-04-16',
    'artist': 'Artist Name',
    'album': 'Name of Album',
    'genre': 'Rock',
}
query_string = "artist == '{artist}' AND album == '{album}'".format(**metadata)

library = iTunes.sources().objectWithName_("Library")
all_tracks = library.libraryPlaylists()[0]
tracks = all_tracks.tracks().filteredArrayUsingPredicate_(NSPredicate.predicateWithFormat_(query_string))


start = 0.0
track_md = []
# extend track duration by N seconds
fudge = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
)
for i, track in enumerate(tracks):
    tno = track.trackNumber()
    title = track.name()
    length = track.duration() + fudge[tno - 1]
    # print u'ffmpeg -i "input.mkv" -map 0:1 -c:a copy -ss {:.03f} -t {:.03f} "{:02d} - {}.dts"'.format(start, length, tno, title)
    track_md.append({
        'track': tno,
        'title': track.name(),
        'start': float('{:.03f}'.format(start)),
        'duration': float('{:.03f}'.format(length)),
    })
    start += length

metadata['tracks'] = track_md

from json import dump
with open('metadata.json', 'w') as rum:
    dump(metadata, rum, indent=2)
