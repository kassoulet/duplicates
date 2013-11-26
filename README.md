Duplicates - Fast File-Level Deduplicator
=========================================

Duplicates use a fast algorithm, try to early reject false positives.

A file is compared to others files, by using, in order:
 - size
 - hash of first KB
 - hash of content

This program uses temporary files and external sort to minimise memory 
utilization. Nothing is stored in memory.

© 2013 Gautier Portet

