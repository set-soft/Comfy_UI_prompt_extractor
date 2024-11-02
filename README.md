# ComfyUI prompt and workflow extractor

The default image saver of ComfyUI, and the one included in many custom nodes, likes to save the prompt and workflow in the PNG
output.

This has advantages:

- One file contain all the information
- You can use an image browser and just drag and drop the image into ComfyUI canvas to load the workflow

And disadvantages:

- Your workflow can be exposed inadvertently
- Big workflows might become an important part of the image size

It only works for PNG files, with its own trade offs:

- (+) Good to impaint
- (-) Really big

So you might want to keep the workflows outside the PNG file, and even compress the PNG to JPG.

Here is when this script comes in handy. The script takes PNG files, extracts the prompt and workflow to separated files.
The JSON files are then compressed and finally ciphered.

The script also saves a version of the PNG without the prompt/workflow, and a JPG version of the file.

It has many options to skip various of the steps.


# Installation

You need Python 3.7 or newer, no extra modules are needed.

To compress the files you need *lzma*, *bzip2* or *gzip* installed. The first is the one that produces smaller files.

To cypher the files you need *gpg* installed and a public/private key pair. The key is associated to an e-mail.
You can specify the e-mail using *--email*, or the **RECIPIENT_EMAIL** environment variable.

The *image magick* tools must be installed in order to compress the files to PNGs.


# Usage examples

To extract the prompt and worflow in all the PNGs of a directory use:

```
python3 prompt_extract.py *.png
```

It will also generate JPGs for all the PNGs. The compression uses 85% quality by default, if you want 90% use:

```
python3 prompt_extract.py --quality 90 *.png
```

If you want to manually choose which files to keep use:

```
python3 prompt_extract.py --keep *.png
```

If you are confident and want to just remove the PNGs and only keep the JPGs use:


```
python3 prompt_extract.py --remove *.png
```

If you want to compress already existing JPGs use:

```
python3 prompt_extract.py *.jpg
```

I usually save the images before the upscaler and/or face restoration in PNG format and the processed image in JPG format.
But sometimes I want to compress the JPGs with less quality, in this case I use the above mentioned command.

If you want to get the JSON files without compression and cypher use:

```
python3 prompt_extract.py --no-compress --no-cypher *.png
```

If you don't want to compress the PNGs use:

```
python3 prompt_extract.py --no-jpg *.png
```

If you want to uncompress and decypher a JSON file use the `prompt_decode.sh` shell script.


# Notes about the difference between the prompt and workflow files

The workflow file contains all the nodes and its sizes and status. So this file is the most important. Loading it in ComfyUI will
reproduce the worflow as it was displayed when saving the image.

The prompt file contains only the nodes executed to generate the image, without the sizes and status. So this file is much smaller
and is enough to regenerate the image, but isn't nice to modify.

