## Loading Data ##

The first step to using the HIDE system is to load reports into the database. HIDE accepts a variety of import formats including
xml, i2b2 XML, PhysioNet-deid format, and copy-and-paste.

### XML ###
HIDE will import data that follows the same XML schema as the example below:

```
<reports>
<report>
<title>document 1 title</title>
<content>This is the content of document 1 and it can <labelname>include</labelname> well-formed xml</content>
</report>
<report>
<title>document 2 title</title>
<content>This is the content of document 2 and it can <labelname>include</labelname> well-formed xml</content>
</report>
</reports>
```

All of the reports imported will be assigned the tags provided in the import interface.

### i2b2 XML ###
HIDE can import the XML files that can be obtained from the i2b2 challenge: https://www.i2b2.org/NLP/DataSets/Main.php

Note: The released xml from i2b2 has an error in it. This must first be fixed before importing the data into HIDE.

### PhysioNet-DEID format ###
HIDE can import the text files from: http://www.physionet.org/physiotools/deid/ and assign tags to all the documents imported

### Copy-and-Paste ###
It is possible to load text directly into the HIDE database. Using this option you can simply
copy and paste a report into the textfield, give a title, and assign tags to the document.