*******
tenjint
*******

This is the tenjint python library that runs within QEMU.  You will need further components in order to get tenjint working on your system.  These are modified versions of tools you may be familiar with, but be aware you must install the versions found in this repository.  These are:

* `Linux <https://www.kernel.org/>`_ (`tenjint repository <https://github.com/bedrocksystems/tenjint-linux>`_)
* `Qemu <https://www.qemu.org/>`_ (`tenjint repository <https://github.com/bedrocksystems/tenjint-qemu>`_)
* `Rekall <https://github.com/google/rekall>`_ (`tenjint repository <https://github.com/bedrocksystems/tenjint-rekall>`_)

These repositories can all be found within the tenjint GitHub project.  tenjint requires that you run a Linux distribution with our Linux kernel on an Intel processor with VT-x (for x86_64) or an ARMv8+ (for ARM64).

Linux
=====

We modified the KVM component within the `Linux kernel <https://www.kernel.org/>`_ in order to facilitate VMI for both x86_64 and ARM64.  We currently maintain `two versions <https://github.com/bedrocksystems/tenjint-linux>`_, the vanilla v5.2.6 as well as the rpi-5.2.y branch for the Raspberry Pi 4.

Qemu
====

tenjint runs within the `Qemu <https://www.qemu.org/>`_ address space with the help of Cython.  Qemu has been `modified <https://github.com/bedrocksystems/tenjint-qemu>`_ to expose the VMI features in KVM to an interface that can be accessed by Cython (or any other library).  Please see the "Getting Started" section below for instructions on starting Qemu with tenjint.

Rekall
======

`Rekall <https://github.com/google/rekall>`_ is framework for memory forensics.  We leverage Rekall to apply semantic knowledge about the guest operating system when inspecting guest memory.  Rekall is generally used with static memory dumps, however we added a `plugin <https://github.com/bedrocksystems/tenjint-rekall>`_ that allows rekall to access the guest memory directly.  This allows Rekall to operate directly on the guest's memory.

Getting Started
===============

You must have compiled and installed the Linux kernel provided in the linux repository within the tenjint project.  Currently, we maintain two branches, v5.2.6-tenjint and rpi-5.2.y-tenjint.  The v5.2.6-tenjint branch builds upon the v5.2.6 Linux kernel tag and the rpi-5.2.y-tenjint branch builds upon the Raspberry Pi rpi-5.2.y branch and runs on the Raspberry Pi 4.  Instructions for building the Linux kernel can be found elsewhere online, but be sure you enable KVM support when configuring your kernel.

We modified Qemu to accept two new machine properties, "vmi" and "vmi-configs" (these are included in the Qemu help text).  The "vmi" property is only available when "kvm" is selected as the Qemu accelerator.  This property allows you to enable vmi by passing "vmi=on" as a machine property.  The "vmi-configs" property is only available when vmi is enabled and is used for passing configuration options to tenjint.  For an example config file as well as an example for starting Qemu with tenjint, please see below.  Instructions for building Qemu can be found in the Qemu README file.

Rekall must also be installed from our repository as it has been updated to be able to access the guest's memory.  To install Rekall, run `sudo python3 ./setup.py install` from within Rekall's repo root directory.  Depending on the guest OS, you may need to generate a rekall profile.  This is nessecary for Linux guest OSs.  For instructions on generating Rekall profiles, see tools/linux/README within the Rekall repository.

Finally, in order to install tenjint, run `sudo python3 ./setup.py install` from this repositories base directory.  tenjint will automatically be run when Qemu is started with vmi enabled.  For usage examples, see below.

Examples
========

Sample Configuration File::

    logging:
        version: 1
        disable_existing_loggers: False
    formatters:
        simple:
        format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers:
        console:
        class: logging.StreamHandler
        level: DEBUG
        formatter: simple
        stream: ext://sys.stdout
    loggers:
        tenjint:
        level: DEBUG
        handlers: [console]
        propagate: no
    root:
        level: DEBUG
        handlers: [console]
    PluginManager:
        plugin_dir: /home/user/tenjint_plugins/
    OperatingSystemConfig:
        rekall_profile: /home/user/images/ubuntu_19_04_x86_64_5.0.0-36-generic.json
    InteractiveShell:
        enable: true
        wait: true

Notice the "plugin_dir" in the "PluginManager" section, this is used to specify the location of all third-party plugins you wish to load.  Additionally, the "enable" option within the "InteractiveShell" section is used to enable the shell for interactive introspection.

Qemu with tenjint enabled on x86_64::

    $ qemu-system-x86_64 -machine accel=kvm,vmi=on,vmi-configs=/home/user/tenjint_config.yml -no-hpet -rtc base=utc,clock=vm,driftfix=none -global kvm-pit.lost_tick_policy=discard -smp 2 -m 2048 -net none -loadvm analysis -hda /home/user/images/ubuntu_19_04_x86_64.qcow2 -monitor telnet:127.0.0.1:5555,server,nowait


Qemu with tenjint enabled on ARM64::

    $ qemu-system-aarch64 -M virt,gic_version=3,accel=kvm,vmi=on,vmi-configs=/home/user/tenjint_config.yml -cpu host -smp 2 -m 2048 -rtc base=utc,clock=vm -bios /usr/share/qemu-efi/QEMU_EFI.fd -drive if=none,file=/home/user/images/ubuntu_19_04_aarch64.qcow2,id=hd0 -device virtio-blk-device,drive=hd0 -device e1000,netdev=net0 -netdev user,id=net0,hostfwd=tcp:127.0.0.1:5555-:22 -monitor tcp:localhost:4444,server,nowait -loadvm analysis

Notice the clock options, these are recommended for use with tenjint.  Additionally, for now tenjint will only work when the guest is started from a snapshot.  Notice both examples assume a snapshot with the name "analysis" has already been created.

API
===

The API reference can be found in the menu.

The API can be used to write third-party plugins.  These plugins simply need to be copied into the plugin directory as specified in the configuration file.  See above for an example.

Contact
=======

The tenjint maintainers can be contacted by emailing

tenjint@bedrocksystems.com

.. toctree::
   :maxdepth: 3
   :hidden:

   api
   rpi
