# Syncthing Restore From Stversions 

One of my drives were corrupted causing all the files inside to be corrupted.
This spread to all my synced devices. However, thankfully, I had staggered
versioning setup with Syncthing.

Syncthing didn't have a way to restore an entire directory and therefore I has
to resort to writing a program myself to restore all the files for my directory. 

This is specifically written for the case where you know all the files in the
original directory and you only want to recovered the last good version from the
`.stversions` directory.

Right now the `main.py` doesn't work yet. Please just run `recovery.py` AFTER
changing the global variable at the top of the script.

## TO DO

Since this way mainly written as a simple program I could use to restore my
data, I didn't put too much effort into the user interface. However, I think it
would be useful to refine it.

If you are someone that needs to use this and either need help or can
contribute, feel free to contact me.

- [ ] Build a CLI user interface to use the program.

- [ ] Build a GUI user interface to use the program.

- [ ] Allow user to restore all files that have a version (case where original
      directory is deleted / some files are moving).

- [ ] Allow user to choose to copy original (possibly corrupt) file from the
      original directory in case a backup does not exist in `.stversions`.
      Note that this is already logged inside of `missing-files.txt` but this
      would make it easier to copy the original version.
