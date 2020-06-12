#!/bin/sh

# Author: Anton Ihonen
# Date: 2020

# The purpose of this script is to compile Kvazaar on Linux.
#
# Usage: kvazaar_compile.sh <$1> <$2> [$3]
# $1 The absolute path of the Kvazaar repository. Must not be an empty string
#  (will produce an error).
# $2 The absolute installation filepath of the Kvazaar binary,
#  i.e. the path to which the executable will be copied after compilation.
#  The directory will be created if it doesn't exist.
#  If the file already exists, execution will be terminated.
#  Must not be an empty string (will produce an error).
# $3 The arguments to be passed to the configure script of Kvazaar.
#  Can be an empty string (will produce a warning).
#
# Returns zero on success, non-zero otherwise.

this_file_name="$(basename "$0")"
echo "--INFO: Running $this_file_name"

# Validate arguments.

for help_arg_str in "--help" "help" "-h" "--h"
do
    if [ "$1" = "$help_arg_str" ]; then
        echo "Usage: kvazaar_compile.sh <repository filepath> <executable dest filepath> [build config args]"
        exit 0
    fi
done

if [ "$1" = "" ]; then
    echo "--ERROR: $this_file_name: Empty argument \$1 (Kvazaar repository path)"
    exit 1
elif [ "$1" != "/*" ]; then
    echo "--WARNING: $this_file_name: Argument \$1 ('$1') is not an absolute path"
fi

if [ "$2" = "" ]; then
    echo "--ERROR: $this_file_name: Empty argument \$2 (Kvazaar binary destination path)"
    exit 1
else
    if [ "$2" != "/*" ]; then
        echo "--WARNING: $this_file_name: Argument \$2 ('$2') is not an absolute path"
    fi
    if [ -e "$2" ]; then
        echo "--ERROR: $this_file_name: File '$2' already exists"
        exit 1
    fi
fi

if [ "$3" = "" ]; then
    echo "--WARNING: $this_file_name: Empty argument \$3 (Kvazaar configure script arguments)"
fi

# Path of the Git repository.
kvz_repo_path="$1"
# The path in which the Kvazaar executable will be found after compilation.
kvz_executable_src_path="$1/src/kvazaar"
# The path of the directory to which the exexutable will be copied.
kvz_executable_dest_dir_path="$(dirname "$2")"
# The path in which the Kvazaar executable will be found after copying.
kvz_executable_dest_path="$2"
# Arguments to be passed to kvazaar/configure.
kvz_configure_args="$3"

# Current working directory.
original_work_dir="$(pwd)"

# Compile Kvazaar as per the instructions in kvazaar/README.md. Exit on failure.
echo "--INFO: $this_file_name: Compiling Kvazaar in directory $kvz_repo_path"
(cd "$kvz_repo_path" && ./autogen.sh && ./configure ""$kvz_configure_args"" && make) || exit 1

cd "$original_work_dir"

# Create the destination directory if it doesn't exist
# or exit if the path is reserved.
if [ ! -d "$kvz_executable_dest_dir_path" ]; then
    if [ -e "$kvz_executable_dest_dir_path" ]; then
        # The path is occupied by something other than a directory.
        echo "--ERROR: $this_file_name: path '$kvz_executable_dest_dir_path' doesn't point to a directory"
        exit 1
    fi
    # Create the path recursively.
    echo "--INFO: $this_file_name: Creating path $kvz_executable_dest_dir_path"
    mkdir "$kvz_executable_dest_dir_path" -p
fi

# Copy the executable to its destination.
echo "--INFO: $this_file_name: Copying $kvz_executable_src_path to $kvz_executable_dest_path"
cp "$kvz_executable_src_path" "$kvz_executable_dest_path"

# Clean up the repository so another version of Kvazaar
# can be built without issues if need be.
echo "--INFO: Cleaning Kvazaar repository $kvz_repo_path"
(cd "$kvz_repo_path" && make clean) || exit 1

cd "$original_work_dir"

exit 0
