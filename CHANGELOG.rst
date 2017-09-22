=========
Changelog
=========

This document records all notable changes to ``zs2decode``.

`0.3.0` (2017-09-22)
---------------------

* Refactored parsing of data in ``QS_`` chunks (0xEE sub-type 0x0011) to be more general. The format code lost its prominent status, affecting the structure of type and format signatures in the output. There is no syntax for unparsed data anymore.
* Utility functions return bytes/bytearray to avoid double-UTF8 encoding of strings.
* Values in XML elements are now JSON encoded rather than based on repr(). This affects the spelling of booleans, and tuples are output as lists.
* Changed order of path elements printed together with closing elements in text output.
* Added and modified format strings for ``QS_`` chunks.
* Chunk names affected by character substitution are now maintained in XML files in the ``name`` attribute.
* Added functionality to encode XML files to zs2.
* Improved platform independence with respect to integer byte lengths.
* Output of audit log decoder has been made more basic to be compatible with syntax fo EE11 ``QS_`` chunks.

`0.2.1-dev` (unreleased)
-------------------------

* Example script ``raw_data_dump_from_xml.py`` can now extract data from zs2 files with slightly different structure.
* ``util.chunks_to_XML()`` will now perform character substitutions if necessary to create valid XML element names. ``util.chunks_to_text_dump()`` continues to maintain the orginal names.
* License included in wheel.
* Added changelog.

`0.2.0` (2017-09-15)
---------------------

* Added interpretation of data type 0xEE, sub-type 0x0005.
* Refactored xml output to perform correct entity substitution.
* Refactored interpretation of single-precision numbers. Previously, some results were not optimal.

`0.1` (2015-12-07)
---------------------

* Initial Release.
