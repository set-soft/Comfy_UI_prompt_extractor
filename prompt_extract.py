#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2024 Salvador E. Tropea
# License: AGPL-3.0
#
# This tool can be used to extract the prompt/workflow stored in PNG images when using ComfyUI
# The prompt is the path of nodes used for generation, without position, status, etc. Is enough to regenerate
# the image, but looks different.
# The workflow contains all nodes and their position and status, looks like what you used in ComfyUI.
# Once extracted to JSON files they are compressed and cyphered.
# You can skip the compression and/or cypher.
# Then save the PNG without the prompt and workflow.
# The script tries to figure out the seed and includes it in the name of the new PNG.
# It finally compresses the new PNG to JPG.
# The original PNG file remains untouched, you get new files.
#
import argparse
import json
import os
import re
import shutil
from struct import unpack
import subprocess
import logging
QUALITY = 85
RECIPIENT_EMAIL = 'salvador@inti.gob.ar'
VERSION = "1.0.0"


def read_png(file):
    with open(file, 'rb') as f:
        s = f.read()
    offset = 8
    ppi = 300
    w = h = -1
    prompt = workflow = ''
    if s[0:8] != b'\x89PNG\r\n\x1a\n':
        logging.error('Not a PNG')
        return None, None, None
    logging.debug('Parsing PNG chunks')
    while offset < len(s):
        size, type = unpack('>L4s', s[offset:offset+8])
        logging.debug(f'- Chunk {type} ({size})')
        if type == b'IHDR':
            w, h = unpack('>LL', s[offset+8:offset+16])
            logging.debug(f'  - Size {w}x{h}')
        elif type == b'pHYs':
            dpi_w, dpi_h, units = unpack('>LLB', s[offset+8:offset+17])
            if dpi_w != dpi_h:
                raise TypeError(f'PNG with different resolution for X and Y ({dpi_w} {dpi_h})')
            if units != 1:
                raise TypeError(f'PNG with unknown units ({units})')
            ppi = dpi_w/(100/2.54)
            logging.debug(f'  - PPI {ppi} ({dpi_w} {dpi_h} {units})')
            break
        elif type == b'tEXt':
            data = s[offset+8:offset+8+size]
            keyword, text = data.split(b'\x00', 1)
            try:
                json_data = json.loads(text.decode('utf-8'))
            except Exception:
                json_data = text.decode('utf-8')
            if keyword == b'prompt':
               prompt = json_data
               logging.debug(f'  - Prompt')
            elif keyword == b'workflow':
               workflow = json_data
               logging.debug(f'  - Workflow')
        elif type == b'IEND':
            break
        offset += size+12
    if w == -1:
        raise TypeError('Broken PNG, no IHDR chunk')
    return s, prompt, workflow, w, h


def write_png(s, file):
    offset = 8
    with open(file, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        while offset < len(s):
            size, type = unpack('>L4s', s[offset:offset+8])
            if type != b'tEXt':
                f.write(s[offset:offset+12+size])
                if type == b'IEND':
                    break
            offset += size+12


def save_text(fname, what, json_data):
    if not json_data:
        return None
    name = fname.replace('.png', f'_{what}.json')
    logging.debug(f'Writing `{what}` to `{name}`')
    with open(name, 'w') as f:
        json.dump(json_data, f, indent=2)
    return name


def remove(fname):
    if not os.path.isfile(fname):
        return
    os.remove(fname)


def compress(name, keep, tool, ext):
    if not name:
        return None
    input_file = name
    output_file = name+'.'+ext
    remove(output_file)
    command = [tool, '-9', '-k', input_file]
    try:
        subprocess.run(command, check=True)
        logging.debug(f"Compressed {input_file} to {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {command}: {e}")
    if not keep:
        remove(input_file)
    return output_file


def cypher(name, email, keep):
    if not name:
        return None
    input_file = name
    output_file = name+'.gpg'
    remove(output_file)
    command = ['gpg', '-e', '-r', email, '-o', output_file, input_file]
    try:
        subprocess.run(command, check=True)
        logging.debug(f"Cyphered {input_file} to {output_file}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {command}: {e}")
    if not keep:
        remove(input_file)
    return output_file


def extract_seed(prompt):
    """ Very naive, works for one worlflow I use """
    if not prompt:
        return None
    for id, node in prompt.items():
        inputs = node.get('inputs', {})
        if not inputs:
            continue
        seed = inputs.get('seed')
        if seed is not None and isinstance(seed, int):
            return seed
    return None


def convert2jpg(fname, quality, keep, out=None):
    input_file = fname
    output_file = out or fname.replace('.png', '.jpg')
    command = ['convert', input_file, '-quality', str(quality), output_file]
    try:
        subprocess.run(command, check=True)
        logging.debug(f"Converted {input_file} to {output_file} with quality {quality}%")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {command}: {e}")
    if not keep:
        remove(input_file)
    return output_file


def is_email_handled_by_gpg(email):
    try:
        result = subprocess.run(['gpg', '--list-keys'], capture_output=True, text=True, check=True)
        return email in result.stdout
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return False


def check_gpg(email, no_cypher):
    if no_cypher:
        return True
    if not shutil.which('gpg'):
        logging.error('No gpg tool installed, disabling cypher')
        return True
    if not is_email_handled_by_gpg(email):
        logging.error(f"The `{email}` doesn't have a key in gpg, provide another with --email")
        return True
    return False


def check_compress(no_compress):
    if no_compress:
        return True, None, None
    if shutil.which('lzma'):
        return False, 'lzma', 'lzma'
    logging.error('No lzma tool installed')
    if shutil.which('bzip2'):
        return False, 'bzip2', 'bz2'
    logging.error('No bzip2 tool installed')
    if shutil.which('gzip'):
        return False, 'gzip', 'gz'
    logging.error('No gzip tool installed, disabling compression')
    return True


def get_jpg_size(image_path):
    with open(image_path, 'rb') as f:
        try:
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                f.seek(size, 1)
                byte = f.read(1)
                while ord(byte) == 0xff:
                    byte = f.read(1)
                ftype = ord(byte)
                size = unpack('>H', f.read(2))[0] - 2
            # We are at a SOFn block
            f.seek(1, 1)  # Skip `precision' byte.
            height, width = unpack('>HH', f.read(4))
            logging.debug(f'  - Size {width}x{height}')
            return width, height
        except Exception as e:
            return None, None
    return None, None


def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="""
    Extracts ComfyUI prompt and workflows from a PNG.
    The JSON files are compressed and cyphered.
    A copy of the PNG is saved without prompt/workflow and compressed to JPG.
    If we find the seed its added to the name.
    """)

    # Add arguments
    parser.add_argument('files', type=str, nargs='*', help="List of file names to process")
    parser.add_argument('--email', type=str, help="E-mail for the GPG key", default=RECIPIENT_EMAIL)
    parser.add_argument('--keep', action='store_true', help="Don't remove previous steps")
    parser.add_argument('--no-compress', action='store_true', help="Don't compress the JSON files")
    parser.add_argument('--no-cypher', action='store_true', help="Don't cypher the JSON files")
    parser.add_argument('--no-jpg', action='store_true', help="Don't compress the PNG to JPG")
    parser.add_argument('--no-png', action='store_true', help="Don't create a PNG without the prompt")
    parser.add_argument('--no-prompt', action='store_true', help="Don't save the prompt")
    parser.add_argument('--no-size-in-name', action='store_true', help="Don't include the size in PNG/JPG name")
    parser.add_argument('--no-workflow', action='store_true', help="Don't save the workflow")
    parser.add_argument('--remove', action='store_true', help="Remove original files")
    parser.add_argument('--quality', type=int, help="JPG quality", default=QUALITY)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--quiet', '-q', action='store_true', help="No progress information")
    group.add_argument('--verbose', '-v', action='store_true', help="Show debug info")
    parser.add_argument('--version', '-V', action='store_true', help="Show version and exit")
    # Parse the arguments
    args = parser.parse_args()

    # Setup the logger
    if args.quiet:
        level = logging.WARNING
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level,
                        format='%(asctime)s - %(levelname)s - %(message)s',  # Define the output format
                        datefmt='%Y-%m-%d %H:%M:%S')  # Date format

    # Version first
    if args.version:
        print(f"prompt_extract {VERSION} - © Copyright 2024, Salvador E. Tropea - License: AGPL v3")
        exit(0)
    # Sanity
    args.no_cypher = check_gpg(args.email, args.no_cypher)
    args.no_compress, compress_tool, compress_ext = check_compress(args.no_compress)
    if not args.files:
        logging.error('No files to process')
        exit(2)

    # Process the files
    for file_name in args.files:
        logging.info(f"Processing file: {file_name}")
        if file_name.endswith('.png'):
            s, prompt, workflow, w, h = read_png(file_name)
            # Save the prompt
            name_prompt = None if args.no_prompt else save_text(file_name, 'prompt', prompt)
            name_prompt_comp = name_prompt if args.no_compress else compress(name_prompt, args.keep, compress_tool, compress_ext)
            name_prompt_cypher = name_prompt_comp if args.no_cypher else cypher(name_prompt_comp, args.email, args.keep)
            # Save the workflow
            name_workflow = None if args.no_workflow else save_text(file_name, 'workflow', workflow)
            name_workflow_comp = name_workflow if args.no_compress else compress(name_workflow, args.keep, compress_tool, compress_ext)
            name_workflow_cypher = name_workflow_comp if args.no_cypher else cypher(name_workflow_comp, args.email, args.keep)
            seed = extract_seed(prompt)
            fname = file_name
            if seed is not None:
                logging.info(f'Found seed {seed}')
                fname = fname.replace('.png', f'_{seed}.png')
            if not args.no_size_in_name:
                fname = fname.replace('.png', f'_{w}x{h}.png')
            fname = fname.replace('.png', f'_no_prompt.png')
            if prompt or workflow and not args.no_png:
                write_png(s, fname)
                if not args.no_jpg:
                    convert2jpg(fname, args.quality, args.keep)
                if args.remove:
                    remove(file_name)
        elif file_name.endswith('.jpg'):
            w, h = get_jpg_size(file_name)
            if w is None:
                logging.info(f'- Skipping JPG with unknown size')
            convert2jpg(file_name, args.quality, not args.remove, out=file_name.replace('.jpg', f'_{w}x{h}.jpg'))
        else:
            logging.info(f'- Skipping unknown extension')

if __name__ == "__main__":
    main()
