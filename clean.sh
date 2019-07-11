#!/bin/bash
sudo -H pip3 uninstall -y tenjint
rm -f tenjint/api/*.c
sudo rm -rf *.egg-info
sudo rm -rf dist/
sudo rm -rf build/
