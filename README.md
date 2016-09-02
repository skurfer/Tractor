# Tractor: The Track Extractor #

## What’s it for? ##

It’s common to find the music from an album in one continuous stream inside a single file. This is especially true for music in surround formats like DTS, Dolby Digital, and LPCM.

This script will extract individual tracks from the original stream and put each one into its own file. By default, only the raw audio data will be written to a file with the appropriate extension. You can optionally place each track into a Matroska container or Apple Lossless file and add metadata.

## What can I use it on? ##

  * MKV containers
  * M4V containers
  * CUE + WAV
  * “Naked” DTS, AC3, MLP, and WAV files
  * Probably any container that FFmpeg supports

## What will I end up with? ##

A folder containing a file for each track. The exact results depend on the format of the audio data and the layout you choose.

Without the `--container` option, the resulting tracks will be either `.dts`, `.ac3`, or `.wav`. With that option, the tracks will be `.mka` (Matroska Audio) or `.m4a` (Apple Lossless).

In all cases, the original audio data should be copied untouched (without transcoding or lossy compression) into the resulting files.

## What do I need to run it? ##

  * [Python 3][python] (It probably runs under 2.7, but that hasn’t been tested.)
  * [FFmpeg][ffmpeg], which does all the hard stuff

## Metadata ##

The script will look for metadata in:

  * The source file names (like `Artist - Album.mkv`)
  * The source container (using `ffprobe`)
  * A JSON file (see [the included example](example.json))
  * A CUE file

In order to function, the script needs at least:

  * Artist
  * Album
  * Track start and end times
  * Track titles

## Examples ##

Run `tractor.py -h` to see all options.

### MKV or M4V Containers ###

For these containers, a JSON file containing the extra metadata will most likely be necessary, but a lot of the data *might* be available from other sources. Specifically:

  * The artist and album names can be pulled from the container filename if it’s formatted as `Artist - Album.mkv`
  * Some applications, like [Handbrake](https://handbrake.fr/), will allow you to enter the names for each track prior to creating the container.
  * If everything goes well, Handbrake will also mark the start of each “chapter” (track) in the stream.

Once you have your source file and metadata ready:

    tractor.py -s 'Album - Artist.mkv' -d album.json -a cover.jpg -c

### CUE + WAV ###

If you end up with this combination, the CUE file will probably specify the path to the WAV containing the data, so you can usually omit that. It should be as simple as:

    tractor.py -d Album.cue -a cover.jpg -c

## Tips ##

* If you specify a release date (and you will, because it’s important and you’re not an animal), follow the format recommended in [the Matroska documentation](https://www.matroska.org/technical/specs/tagging/index.html#why)
* When attaching artwork to a Matroska container, the original filename will also be stored in the container. You’ll probably never see it, but just in case, you might want to give it a reasonable name like “cover.jpg” prior to using Tractor.
* If using a CUE file, check the metadata before using Tractor. (It’s just a text file that you can modify with the editor of your choice.) Genre is often missing or wrong. Release date is often missing, wrong, or not formatted according to the Matroska spec. Track names are often capitalized incorrectly. You get the idea.
* Streams are numbered starting with 0 and the first is *usually* video we’re not interested in. As a result, Tractor defaults to stream 1 unless you tell it otherwise. If the source container has both DTS and 24-bit stereo and you want to get both, you’ll need to specify each stream, one at a time.
* If the source file is just plain audio data (no container), there will only be one stream, so Tractor will default to stream 0.

### Handbrake vs. MakeMKV ###

The short version is “use Handbrake when possible” (with the appropriate “Passthru” audio option). It will allow you to pre-define the track names and it will mark the start of each track automatically. With [MakeMKV](http://www.makemkv.com/), you’ll get the data and that’s it. Names and start times will need to determined with trial and error, then entered by hand.

So why would you ever use MakeMKV? Because it almost always works and it doesn’t try to do anything “smart” to the data. It just copies it.

I’ve seen the following problems with Handbrake:

  * Unable to read the layout of the source disc.
  * The Passthru option doesn’t copy the original data untouched.
  * The index is corrupt or can’t be understood, so the track durations get messed up. Usually this is very obvious because it will think the first several tracks are 0.033 seconds long, and the final track is a full hour. Note that in this case, the data is probably still usable and the track names are in place. You just need to manually give start times.

### Using FFmpeg Directly ###

In a lot of cases, the GUI tools will fail you. They really depend on indexes and layouts and such. If that information is corrupt or confusing to the app in some way, it might omit some titles, entire chunks of a stream, or just refuse to read the disc at all. It’s not hopeless though. You might be able to get the data using FFmpeg.

To see what’s available on the disc in Title 1, go into the `VIDEO_TS` folder and try this:

    cat VTS_01_?.VOB | ffprobe -

If you see the stream, you might be able to pull it out. Assuming the DTS data is in stream 2:

    cat VTS_01_?.VOB | ffmpeg -i - -c:a copy -map 0:2 ~/Desktop/out.dts

A similar technique can be used if the data is in `AUDIO_TS`.

## Why? ##

### Why Matroska Audio? ###

Matroska containers don’t care what you put in them, so they’re a perfect choice for DTS, Dolby Digital, 6 channel LPCM, etc.

### Why Apple Lossless? ###

One obvious reason is that it’s lossless. DVD and Bluray albums often contain 24-bit stereo versions of the music. No point in pulling that out if you’re going to throw away most of the data.

So why not FLAC? Most players support FLAC, with one monumental exception: iTunes. But iTunes *does* support Apple Lossless (ALAC) and, because it’s been open source for many years now, so do all the other players.

## Other Tools ##

Two other scripts can be found in this repository.

### `tagdts.py` ###

If you find yourself with a collection of “naked” DTS, WAV, or AC3 files, you can use this script to put them into containers with metadata.

### `itunes_info.py` ###

This script is useful in the following scenario:

  * Handbrake mangled the chapter start/duration info, or you used MakeMKV and that info doesn’t even exist
  * You already own the stereo version of the album and have it in iTunes
  * You’re using macOS

It’s more common than you might think.

To use this script, you’ll need to edit it. Enter the artist, album, etc. at the top before you run it. It will search iTunes and put the resulting metadata in a JSON file you can then use with Tractor.

It will get the track names, which is nice, but its main purpose is to get the approximate durations so you don’t have to do quite as much trial and error.

The bad news is, you will still need to do a lot of trial and error. For whatever reason, the length of each track on the surround version never exactly matches the CD or downloaded release.

You’ll need to generate the JSON, use Tractor to create the tracks, then listen to make sure they start and stop in the right place. If (when) they don’t, that’s what the “fudge” tuple in the script is for. If the second track needs to play 1.7 seconds longer, enter 1.7 as the second number. Use negative numbers to pull the duration back a bit. Then repeat and repeat until it sounds right to you.

One last important note: This script relies on Scripting Bridge, which will only work with the version of Python bundled with macOS. So, run it as:

    /usr/bin/python itunes_info.py

[python]: https://www.python.org/
[ffmpeg]: http://ffmpeg.org/
[mka]: https://www.matroska.org/
