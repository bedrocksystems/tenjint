#!/bin/bash

# Clean
rm -rf generated
rm -rf html

# build
python3 generate_api_rst.py
sphinx-build -b html . html

# publish. Todo.
