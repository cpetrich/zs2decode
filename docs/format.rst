The zs2 file format
===================

File structure
--------------

Compression
^^^^^^^^^^^
``zs2`` files are `gzip-compressed`_ binary files. The first step to
decoding a file is to unpack the ``zs2`` file with a utility program 
such as ``gunzip`` or `7-zip`_, or opening the file using the 
`Python module`_ ``gzip``. This results in a binary data stream.

.. cssclass:: table-bordered

 +----+--------------------+----+
 |       gzip compression       |
 +----+--------------------+----+
 |    |                    |    |
 |    |     data stream    |    |
 |    |                    |    |
 +----+--------------------+----+
 

.. _gzip-compressed: https://en.wikipedia.org/wiki/Gzip
.. _7-zip: http://www.7-zip.org/
.. _Python module: https://docs.python.org/2/library/gzip.html

Data stream structure
^^^^^^^^^^^^^^^^^^^^^
The data stream starts with a header signature, followed by combinations 
of chunks and filler bytes, and a final end-of-file (EOF) marker.
A typical ``zs2`` file contains over 100,000 chunks.

 +--------------------+--------+
 | Header (4 bytes)            |
 +--------------------+--------+
 | Chunk 1                     |
 |                             |
 +--------------------+--------+
 | Chunk 2                     |
 |                             |
 +--------------------+--------+
 | ...                         |
 |                             |
 +--------------------+--------+
 | Chunk n                     |
 |                             |
 +--------------------+--------+
 
 
Byte order
~~~~~~~~~~
The `byte order`_ of the *binary file* is **little-endian**. For
example, a 32-bit representation of the integer value ``1`` 
in the data stream would be ``0x01 0x00 0x00 0x00``.

.. _byte order: https://en.wikipedia.org/wiki/Endianness

Header
^^^^^^
The *binary file* starts with the 4-byte signature ``0xAF 0xBE 0xAD 0xDE``, 
i.e. ``0xDEADBEAF`` in hexadecimal or ``3735928495`` in decimal. 

 +----------+----------+----------+----------+
 | Offset 0 | Offset 1 | Offset 2 | Offset 3 |
 +==========+==========+==========+==========+
 | ``0xAF`` | ``0xBE`` | ``0xAD`` | ``0xDE`` |
 +----------+----------+----------+----------+

This signature is followed immediately by the first chunk.

Chunks
^^^^^^
Chunks contain information on data stream structure, metadata or data.

With the exception of the "End-of-Section" chunk, 
all chunks follow the same general structure:
an ASCII-encoded name of the chunk type, starting 
with one byte length giving the length of the name
in bytes (Section :ref:`section-ascii-string-definition`), 
followed by the data type of the particular
chunk (Section :ref:`section-data-types`) and actual chunk 
data. In contrast, the End-of-Section chunk is simply
a single byte of value ``0xFF``. Both chunk structures
can be discriminated between because chunk type names 
do not start with ``0xFF``.

The following chunk structures are possible:
 
 +------------+------------+------------+------------+
 | Chunk type name         | Data type  | Chunk      |
 |                         | code       | data       |
 +============+============+============+============+
 | ASCII-encoded, at least | 1 byte     | 1 or more  |
 | 2 bytes                 |            | bytes      |
 +------------+------------+------------+------------+
 
or, for the "End-of-Section" chunk,
 
 +------------+------------+------------+------------+
 | End of     |            |            |            |
 | Section    |            |            |            |
 +============+============+============+============+
 | ``0xFF``   |            |            |            |
 |            |            |            |            |
 +------------+------------+------------+------------+
 
The total length of the chunk can be anywhere from 1 byte upward.
In particular, the total chunk length is generally not a 
multiple of 2 or 4 bytes.

.. note:: Less than 5% of the existing chunk types have no data type.

An example of a chunk with chunk type name ``ID`` would be: 

 +--------+--------+--------+--------+--------+--------+
 | Chunk type name          | Data   | Chunk data      |
 +--------+--------+--------+ type   +                 +
 | Length | Name            |        |                 |
 +--------+--------+--------+--------+--------+--------+
 | ``2``  | ``I``  | ``D``  |``0x66``| ``48154``       | 
 +========+========+========+========+========+========+
 | 1      | 2      | 3      | 4      | 5      | 6      | 
 +--------+--------+--------+--------+--------+--------+
 |``0x02``|``0x49``|``0x44``|``0x66``|``0x1A``|``0xBC``|
 +--------+--------+--------+--------+--------+--------+

.. _section-chunk-naming:

Chunk type naming
^^^^^^^^^^^^^^^^^
Chunk type names are ASCII strings defined in 
Section :ref:`section-ascii-string-definition`.
Chunk types names are chosen to be readable ASCII text, 
comprising only of underscore (``_``), 
digits ``0`` to ``9``, and English letters ``A`` to ``Z`` and ``a`` to ``z``.
Their length is limited to 254 characters since an indicated length of 
``255`` (``0xFF``) represents an "End-of-Section" chunk.
Also, chunk type names of length 0 (``0x00``) do not exist.

The three chunk types ``Key``, ``Elem``, and ``Val`` represent list items. 
Digits are used at the end of chunk type names to enumerate the list items.
Within each list, numbers are consecutive in decimal format, 
starting with zero. 
For example, the list element ``Elem0`` will be followed by ``Elem1``. 
``Elem9`` will be followed by ``Elem10`` etc. 
If a list has only one entry, the number will be zero (e.g. ``Key0``).


.. note:: By convention, most chunk type names start with a capital letter 
          ``A`` to ``Z`` and use *CamelCase* spelling for compound words 
          (i.e., approximately 95% of all chunk type names).
          Names are derived from either English or German language.
          The shortest chunk type names are ``x``, ``y``, ``X``, and ``Y``. 
          The longest chunk type name is
          ``AssignmentBetweenOrganizationDataAndTestProgramParamIds``
          at 55 characters.

Order of chunks
^^^^^^^^^^^^^^^
The order of some chunks is significant as they can establish
a partitioning into sections (chunks of data type ``0xDD`` start
a section that corresponding "End-of-Section" chunks end), chunk
lists (starting with the ``Count`` chunk), or key-value assignment
(``Key`` chunks immerdiately preceeding an ``Elem`` chunk).
Beyond that, chunk order seems to be free but follows predictable,
machine-generated patterns.

.. note:: The actual degree of flexibility in chunk ordering is defined
          by the implementation of the ``textXpert II`` parser, which is
          not known.
		  
End-of-Section chunks
^^^^^^^^^^^^^^^^^^^^^
"End-of-Section" chunks contain only one byte, ``0xFF``.
They can be discriminated from regular chunks in that chunk type names
of length ``255`` (``0xFF``) do not exist. 
End-of-Section chunks terminate the most recent section started 
by a ``0xDD`` chunk.

End of data stream
^^^^^^^^^^^^^^^^^^
The end of the data stream is marked by the "End-of-Section" chunk that
terminates the root section of the data stream (the first chunk in the
data stream is of type ``0xDD``).

.. _section-data-types:
 
Data type codes
---------------
The 1-byte data type code determines type and, in most cases, the 
length of the chunk data section in bytes. A chunk type may appear
with different data codes throughout the data stream.
The following type codes exist:
 
 +-----------+------------+----------------------------------------+
 | Data type | Length of  | Type of data                           |
 | code      | chunk data |                                        |
 +===========+============+========================================+
 | ``0x11``  |          4 | Integer [#intdef]_                     |
 +-----------+------------+----------------------------------------+
 | ``0x22``  |          4 | Unsigned integer: value                |
 +-----------+------------+----------------------------------------+
 | ``0x33``  |          4 | Signed integer: coordinates            |
 +-----------+------------+----------------------------------------+
 | ``0x44``  |          4 | Unsigned integer: flag, color code     |
 +-----------+------------+----------------------------------------+
 | ``0x55``  |          2 | Integer [#intdef]_                     |
 +-----------+------------+----------------------------------------+
 | ``0x66``  |          2 | Integer [#intdef]_                     |
 +-----------+------------+----------------------------------------+
 | ``0x88``  |          1 | Unsigned byte: type code               |
 +-----------+------------+----------------------------------------+
 | ``0x99``  |          1 | Boolean: ``0``\ =False, ``1``\ =True   |
 +-----------+------------+----------------------------------------+
 | ``0xAA``  | at least 4 | Unicode string [#aaee]_                |
 +-----------+------------+----------------------------------------+
 | ``0xBB``  |          4 | Single precision floating point number |
 +-----------+------------+----------------------------------------+
 | ``0xCC``  |          8 | Double precision floating point number |
 +-----------+------------+----------------------------------------+
 | ``0xDD``  | at least 1 | Document section start [#ddtype]_      |
 +-----------+------------+----------------------------------------+
 | ``0xEE``  | at least 6 | List of data [#aaee]_                  |
 +-----------+------------+----------------------------------------+

Data types ``0x00``, ``0x77``, and ``0xFF`` do not appear.

.. [#intdef]  The interpretation of integers of data type codes 
              ``0x11``, ``0x55`` and ``0x66`` depends on context. 
              They may be either signed or unsigned, depending on 
              the chunk type rather than the data type code.
              Data type code ``0x11`` is used for a range of 
              purposes, including color codes (which would 
              typically be interpreted as unsigned 
              hexadecimal values) and flags of value 
              ``0xffffffff`` (which would typically be written 
              as signed ``-1`` rather than unsigned ``4294967295``).

.. [#aaee]  The length of the chunk data field for data types 
            ``0xAA`` and ``0xEE`` is encoded as part of the 
            chunk data. See also Section
            :ref:`section-data-list-definition`.

.. [#ddtype]  Data type ``0xDD`` indicates that a chunk marks the 
              beginning of a structural or logical **section**. 
              The length of the chunk data field is encoded as part
              of the chunk data.
              Chunk data contain an ASCII-encoded section descriptor
              that may be empty 
              (see Section :ref:`section-ascii-string-definition`).

Chunk data
----------

Data values
^^^^^^^^^^^
The chunk data section of all data types except ``0xAA``, ``0xDD``,
and ``0xEE`` contains one numerical or boolean value.

In multi-byte data sections, data are arranged ``LSB`` to ``MSB``
and interpreted according to the table on data type codes.

Data structures
^^^^^^^^^^^^^^^
All variable-length structures are stored following a common pattern.
There are three types of variable-length data structures,

 * ASCII strings,
 * lists, and
 * unicode strings.

Each of them is preceeded by the length of the structure in multiples
of the units they contain.
For example, unicode strings will be preceeded by the number of logical 
characters rather than bytes, and lists will be preceeded by the number 
of entries in the list. (List entries are either numbers, strings, or 
n-tuples.) As a result, empty lists and empty strings are represented 
by a length indicator of ``0``.

.. _section-ascii-string-definition:

ASCII strings
~~~~~~~~~~~~~
ASCII-encoded strings are not intended to be printed to the user but help
stucture the document. They appear at two places: the chunk type name, 
and the section descriptor in chunks of data type ``0xDD``.

 +--------+--------+--------+--------+
 | ASCII string                      |
 +--------+--------+--------+--------+
 | Length | Characters               |
 +========+========+========+========+
 | 0      | 1      | ...    | n      |
 +--------+--------+--------+--------+
 | n      | first  | ...    | last   |
 +--------+--------+--------+--------+

Chunk type names are at least one character in length while
empty ASCII strings may appear as section descriptors.

 +--------+--------+--------+--------+
 | Empty ASCII string                |
 +--------+--------+--------+--------+
 | Length | Characters               |
 +========+========+========+========+
 | 0      |        |        |        |
 +--------+--------+--------+--------+
 |``0x00``|        |        |        |
 +--------+--------+--------+--------+

.. _section-data-list-definition:

Lists of data
~~~~~~~~~~~~~
Chunk data of variable length are always encoded in a particular lists
format. 
Lists start with an indication of the number of items in the list. 
This list length is encoded as 4-byte integer and may be ``0`` if no 
list items follow. Bit 31 of the list length is ``0`` as this bit is
used as a marker for strings. Hence, lists can have up to
2,147,483,647 entries.
The list length parameter is followed by exactly the number of list 
items specified.
All list items have the same data type. 
List items may be n-tuples with constituents comprising different 
data types.

Example of an empty list:

 +--------+--------+--------+--------+
 | Number of items in the list       |
 +--------+--------+--------+--------+
 | ``0``                             |
 +========+========+========+========+
 | 1      | 2      | 3      | 4      |
 +--------+--------+--------+--------+
 |``0x00``|``0x00``|``0x00``|``0x00``|
 +--------+--------+--------+--------+

Example of a list containing 2 single-precision floating point numbers, 
``10.1`` and ``1.0``:

 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 | Number of items in the list       |  Single-precision float           | Single-precision float            |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 | ``2``                             | ``10.1``                          | ``1.0``                           |
 +========+========+========+========+========+========+========+========+========+========+========+========+
 | 1      | 2      | 3      | 4      | 5      | 6      | 7      | 8      | 9      | 10     | 11     | 12     |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |``0x02``|``0x00``|``0x00``|``0x00``|``0x9A``|``0x99``|``0x21``|``0x41``|``0x00``|``0x00``|``0x80``|``0x3F``|
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+

Example of a list of 2 tuples that combine a 4-byte integer with a single-precision floating point number, 
``(1, 10.1)`` and ``(2, 1.0)``:

 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 | Number of items                   |  Tuple 1                                                              |  Tuple 2                                                              |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+ 
 | ``2``                             | ``1``                             | ``10.1``                          | ``2``                             | ``1.0``                           |
 +========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+========+
 | 1      | 2      | 3      | 4      | 5      | 6      | 7      | 8      | 9      | 10     | 11     | 12     | 13     | 14     | 15     | 16     | 17     | 18     | 19     | 20     |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |``0x02``|``0x00``|``0x00``|``0x00``|``0x01``|``0x00``|``0x00``|``0x00``|``0x9A``|``0x99``|``0x21``|``0x41``|``0x02``|``0x00``|``0x00``|``0x00``|``0x00``|``0x00``|``0x80``|``0x3F``|
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+

 
.. _section-unicode-string-definition:

Unicode strings
~~~~~~~~~~~~~~~
All characters and strings intended to de displayed to humans 
are encoded in unicode `UCS-2/UTF-16`_ format.
Each character unit is two 2 bytes long. 
Strings are lists 2-byte long elements with
bit 31 of the list length set to ``1`` (*"bit-31 marker"*).

For example, the Norwegian interjection *Skål* would be represented as

 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 | String length with bit-31 marker  |                 |                 |                 |                 |
 |                                   |   S             |   k             |    å            |   l             |
 +========+========+========+========+========+========+========+========+========+========+========+========+
 | 1      | 2      | 3      | 4      | 5      | 6      | 7      | 8      | 9      | 10     | 11     | 12     |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |``0x04``|``0x00``|``0x00``|``0x80``|``0x53``|``0x00``|``0x6B``|``0x00``|``0xE5``|``0x00``|``0x6C``|``0x00``|
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+

.. _UCS-2/UTF-16: https://en.wikipedia.org/wiki/UTF-16


Data type ``0xAA``
^^^^^^^^^^^^^^^^^^
Chunk data of chunks with data type ``0xAA`` contain exactly 
one unicode string (see Section :ref:`section-data-list-definition`).
For example, data type code and chunk data of the string "Hi" would be:

 +--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |        | Chunk Data                                                            |
 +        +--------+--------+--------+--------+--------+--------+--------+--------+
 | Data   | String length with bit-31 marker  |                 |                 |
 | type   |                                   |   H             |    i            |
 +========+========+========+========+========+========+========+========+========+
 | 0      | 1      | 2      | 3      | 4      | 5      | 6      | 7      | 8      |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |``0xAA``|``0x02``|``0x00``|``0x00``|``0x80``|``0x48``|``0x00``|``0x69``|``0x00``|
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+

Data type ``0xDD``
^^^^^^^^^^^^^^^^^^
Chunks of type ``0xDD`` start a structural section that is ended by
a corresponding End-of-Section chunk. The chunk data contain exactly
one ASCII-encoded string that serves as a section descriptor. For example,
data type code and section desciptor "Hi" would be:

 +--------+--------+--------+--------+
 | Data   | Chunk data               |
 +        +--------+--------+--------+
 | type   | Length | H      | i      |
 +========+========+========+========+
 | 0      | 1      | 2      | 3      |
 +--------+--------+--------+--------+
 |``0xDD``|``0x02``|``0x48``|``0x69``|
 +--------+--------+--------+--------+

Without section descriptor, data type code and chunk data would be:

 +--------+--------+
 | Data   | Chunk  |
 | type   | data   |
 +        +--------+
 |        | Length |
 +========+========+
 | 0      | 1      |
 +--------+--------+
 |``0xDD``|``0x00``|
 +--------+--------+

Data type ``0xEE``
^^^^^^^^^^^^^^^^^^
Chunk data of type ``0xEE`` contain one list. The chunk data
start with a 2-byte long header that specifies the type of data in 
the array, followed by a list as defined in 
Section :ref:`section-data-list-definition`.

There are at least five different list data types defined as part of
data type ``0xEE``, which are ``0x0000``,
``0x0004``, ``0x0005``, ``0x0011``, and ``0x0016``.

 +----------+------------+-----------+---------------------------------+
 | Data type|  Sub-type  |Byte-length| Type of list elements           |
 |          |            |of elements|                                 |
 +==========+============+===========+=================================+
 | ``0xEE`` | ``0x0000`` | n/a       | n/a: empty list                 |
 +----------+------------+-----------+---------------------------------+
 | ``0xEE`` | ``0x0004`` | 4         | single-precision floating point |
 +----------+------------+-----------+---------------------------------+
 | ``0xEE`` | ``0x0005`` | 8         | double-precision floating point |
 +----------+------------+-----------+---------------------------------+
 | ``0xEE`` | ``0x0011`` | 1         | bytes of structured data record |
 +----------+------------+-----------+---------------------------------+
 | ``0xEE`` | ``0x0016`` | 4         | integer or boolean              |
 +----------+------------+-----------+---------------------------------+

The byte-list of sub-type ``0x0011`` is a wrapper for a mixed-type
data record whose interpretation depends on the chunk type
(see Section :ref:`section-ee11`).
This sub-type is used by the ``ZIMT`` script for measurement parameters 
and settings, and to store the event audit log.

Sub-types ``0x0004`` and ``0x0005`` are used to store measurement time series recorded by
the testing machine.

Placeholder lists have sub-type ``0x0000``, followed by an empty list.

Sub-type ``0x0016`` seems to be used only to hold boolean values, with
``0x00000000`` and ``0x00000001`` representing ``False`` and ``True``,
respectively.

For example, data type code and chunk data of a list of sub-type ``0x0016``, 
representing a list with one integer element of value ``0x12345678``, 
would be:

 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |        | Chunk Data                                                                              | 
 +        +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 | Data   | Sub-type        | Number of list                    | List element                      |
 | type   |                 | entries                           |                                   |
 +========+========+========+========+========+========+========+========+========+========+========+
 | 0      | 1      | 2      | 3      | 4      | 5      | 6      | 7      | 8      | 9      | 10     |
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 |``0xEE``|``0x16``|``0x00``|``0x01``|``0x00``|``0x00``|``0x00``|``0x78``|``0x56``|``0x34``|``0x12``|
 +--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+--------+
 
Chunk lists
-----------
Chunk lists are elements of the document structure. They consist of a 
chunk of type ``Count`` specifying the number of items in the chunk list, 
followed by a succession of exactly that number of list items. 
Chunk lists can be nested.

The three chunk types ``Key``, ``Elem``, and ``Val`` represent list items. 
They end always on an ordinal number in decimal representation (see
Section :ref:`section-chunk-naming`), i.e., ``0`` in the example in the table:

 +----------+--------------------------------------------------+
 | Chunk    | Use                                              |
 | type     |                                                  |
 | name     |                                                  |
 +==========+==================================================+
 | ``Key0`` |  Singular list item with information stored      |
 |          |  in chunk data of ``Key0``. This chunk may       |
 |          |  immediately preceede an ``Elem`` chunk of the   |
 |          |  same enumeration (i.e., ``Elem0`` in this case).|
 +----------+--------------------------------------------------+
 | ``Elem0``|  Singular list item with information stored in   |
 |          |  chunk data of ``Elem0``, or marker of the       |
 |          |  beginning of a list item with information       |
 |          |  stored in subsequent chunks                     |
 |          |  (data type ``0xDD``).                           |
 +----------+--------------------------------------------------+
 | ``Val0`` |  Singular list item, information is stored       |
 |          |  in chunk data of ``Val0``.                      |
 +----------+--------------------------------------------------+

The ``Count`` chunk is preceeded by a structural chunk of data type 
``0xDD`` that indicates the type of content or purpose of the list. 
That preceeding chunk type does not need to be unique in the data stream.
