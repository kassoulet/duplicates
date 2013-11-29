Duplicates - Fast File-Level Deduplicator
=========================================

Duplicates use a fast algorithm, to early reject false positives.

A file is compared to others files, by using, in order:
 - size
 - hash of first KB
 - hash of content

This program uses temporary files and external sort to minimise memory 
utilization.

© 2013 Gautier Portet

