****************************
tenjint Raspberry Pi 4 Image
****************************

For your convenience, we have generated a Raspberry Pi 4 image with everything you need pre-installed.  This Ubuntu-based image will allow you to try tenjint on ARM without having to install or configure a thing.  The image even contains a simple linux VM.

To get started download the image from the link below and unzip to obtain the image.

`tenjint RPI4 Image <https://drive.google.com/uc?export=download&id=14my428a7FvV7cBqeMhRxIEA6pkTMtLvX>`_

Please be aware that Google will warn you the file is too large for them to scan for viruses.  Please be assured the file is completely safe to download.

Applying the Image
==================

In order to use the image you will first need an SD-card with at least 32GB of capacity.

Once unzipped, you will have an img file called *rpi_official.X.Y.img*.  You will have to apply this image to your SD-card.  On Linux, the easiest way to do this using the ``dd`` utility.  For example,

    $ dd if=/path/to/rpi_official.X.Y.img of=/dev/sdX bs=1K

**WARNING:** *Make sure you know what you are doing.  The* ``/dev/sdX`` *path must be a path to the SD-card device node.  If you choose the incorrect device node, you may overwrite data on other disks and destroy your installation.*

If you rather not use the ``dd`` utility or you are using Windows, please follow the instructions for applying an image from the here: https://www.raspberrypi.org/documentation/installation/installing-images/windows.md

Booting the Image
=================

Once you have applied the image to an SD-card, insert the card into the RPI4's SD-card slot and boot the device.  The image contains a simple desktop environment for your convenience.

**The default username and password is:** user/password

Starting tenjint
================

Once you are booted into the system, open a terminal and run the following command:

    $ start_tenjint.sh

This will automatically start a tenjint instance with the default guest VM.

All images and configuration files can be found in ``/home/user/.tenjint``.  If you want to install custom plugins, you may add them to the ``/home/user/.tenjint/plugins/`` folder.

Questions or Issues
===================

For any questions or issues, please email us at tenjint@bedrocksystems.com

Also, feel free to file a bug report in GitHub if you come across any issues.