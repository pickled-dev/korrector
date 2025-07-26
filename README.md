# Korrector
A small script that reads a Komga database and alters the names of books in the database to more easily facilitate the importation of DieselTech's reading lists.

Doesn't alter anything that can't be changed by a user in the Web UI. Only works as intended if the comics have been tagged properly with either Metron of ComicVine (though I've only tested with Metron).

For one-shots the ComicInfo.xml file must be read, so the script will extract the ComicInfo.xml to read it, but will not alter it.

Backup your database before running this script, just in case something goes wrong. Use the `--backup` and specify a directory create a backup of the database before running the script.