# Tenerezza English Patch

An English translation patch for the Japanese Xbox release of **Tenerezza**.
You need your own Japanese game ISO as no game files or copyrighted work is distributed here,
and Python 3.10 or newer.

I do not have any plans to adapt this for the PC release at this time.

This was translated with the assistance of OpenAI Codex. The text was reviewed and edited by a human where necessary.
The translation methodology sourced as much information about the game laid across the internet and read through the text of the game to establish profiles for the setting and the characters to establish their tone and word choices when applicable. The game itself had fairly easily translatable text, so only a few liberties were taken, mostly with Chocoletta's character and map names.

## Using the patcher

Keep the files arranged like this:

```text
tenerezza_patch.py
tools/
    xdelta.exe
    extract-xiso.exe
xdeltas/
    default.xbe.xdelta
    GPARTS.PAK.xdelta
    SCRIPT.PAK.xdelta
```

Place your Japanese ISO beside the script, then run:

```bat
python tenerezza_patch.py
```

Or specify the ISO directly:

```bat
python tenerezza_patch.py "Tenerezza (Japan).iso"
```

The script extracts the game, checks the original files, applies the patches,
and creates **Tenerezza (English).iso**. It deletes its extracted `source/`
directory when finished. Your original ISO is kept.

Use a folder without an existing `source/` directory. If an English ISO already
exists, add `--overwrite` to replace it.

## Patching manually

Extract your Japanese ISO with an Xbox ISO extraction tool. Apply each xdelta
patch to its matching original file:

| Patch | Original file |
| --- | --- |
| `default.xbe.xdelta` | `default.xbe` |
| `GPARTS.PAK.xdelta` | `GPARTS.PAK` |
| `SCRIPT.PAK.xdelta` | `SCRIPT.PAK` |

You can use an xdelta patching application or run commands like this:

```bat
tools\xdelta.exe -d -s source\default.xbe xdeltas\default.xbe.xdelta source\default.xbe.new
tools\xdelta.exe -d -s source\GPARTS.PAK xdeltas\GPARTS.PAK.xdelta source\GPARTS.PAK.new
tools\xdelta.exe -d -s source\SCRIPT.PAK xdeltas\SCRIPT.PAK.xdelta source\SCRIPT.PAK.new
```

After all three patches succeed, replace the originals with the `.new` files,
removing `.new` from their names. Keep the other extracted files unchanged.
Rebuild the ISO with your Xbox ISO tool, or run:

```bat
tools\extract-xiso.exe -c source "Tenerezza (English).iso"
```

## Support

If you enjoy this translation, please consider supporting me on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/beanutroms)
