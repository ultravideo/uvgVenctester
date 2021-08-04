#!/bin/bash

# root directory for all of the sequences
SEQUENCE_DIR="/path/to/sequences"
# output directory for the results. NOTE: the test configuration must include
# /out/ at the beginning of the output files i.e. /out/example.csv
OUTPUT_DIR="/path/to/output"
# Optional directory where the source files are stored
SOURCE_DIR="/path/to/source"
# Optional directory where the binaries are stored
$BINARY_DIR="/path/to/binaries"
# Optional directory where the encoded sequences and other intermediate files
# are stored
ENCODINGS_DIR="/path/to/encodings"

docker run \
  -v "$SEQUENCE_DIR":/test_seqs \
  -v "$OUTPUT_DIR":/out \
  venctester $1

# If you'd like for the source files and encodings to persist uncomment this
# command and comment the other one
#docker run \
#  -v "$SEQUENCE_DIR":/test_seqs \
#  -v "$OUTPUT_DIR":/out \
#  -v "$SOURCE_DIR":/source \
#  -v "$BINARY_DIR":/binaries \
#  -v "ENCODINGS_DIR":/encodes \
#  venctester $1
