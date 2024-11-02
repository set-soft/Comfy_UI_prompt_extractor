#!/bin/sh
# Decodes the FILE.json.COMPRESS.gpg to FILE.json
#
#
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 compressed_and_cyphered_prompt"
    exit 1
fi

filename="$1"
base_name_1="${filename%.*}"
penultimate_extension="${base_name_1##*.}"
base_name_2="${base_name_1%.*}"

case "$penultimate_extension" in
    gz)
        decompressor="gzip"
        ;;
    bz2)
        decompressor="bzip2"
        ;;
    lzma)
        decompressor="lzma"
        ;;
    *)
        echo "Unsupported compression extension: $penultimate_extension"
        exit 1
        ;;
esac

gpg -d -r $RECIPIENT_EMAIL $filename | $decompressor -d > $base_name_2
