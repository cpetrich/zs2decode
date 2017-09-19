=========
Changelog
=========

This document records all notable changes to ``zs2decode``.

`0.2.1-dev` (unreleased)
-------------------------

* Example script raw_data_dump_from_xml.py can now extract data from zs2 files with slightly different structure.
* util.chunks_to_XML() will now perform character substitutions if necessary to create valid XML element names. util.chunks_to_text_dump() continues to maintain the orginal names.
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
