Duplicates - Fast File-Level Deduplication
==========================================

Duplicates uses a very fast algorithm, to early reject false positives.

A file is compared to others files, by using, in order:
 - its size,
 - the hash of first KB,
 - the hash of content.

This program uses temporary files and external sort to minimise memory 
utilization. It can process millions of files very efficiently.

By default it prints the duplicated files. With '--fix' option, it will
deduplicate files by creating hardlinks.

© 2013 Gautier Portet

