#!/usr/bin/env python3
"""
BlenderMCP安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="blender-mcp",
    version="0.2.0",
    author="xiguadaddy",
    author_email="kangdong303@gmail.com",
    description="通过网络API控制Blender的工具包",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xiguadaddy/blender-mcp",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "socket",
        "json",
    ],
    entry_points={
        "console_scripts": [
            "blender-mcp=blender_mcp_new.cli:main",
        ],
    },
) 
 