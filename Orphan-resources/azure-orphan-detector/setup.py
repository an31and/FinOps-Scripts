#!/usr/bin/env python3
"""Setup script for Azure Orphan Detector"""
from setuptools import setup, find_packages

setup(
    name="azure-orphan-detector",
    version="2.0.0",
    description="Ultra-modular Azure orphaned resources detection system",
    author="Azure Cost Optimization Team",
    packages=find_packages(),
    install_requires=[
        "azure-identity>=1.12.0",
        "azure-mgmt-resource>=21.0.0",
        "azure-mgmt-compute>=29.0.0",
        "azure-mgmt-network>=22.0.0",
        "azure-mgmt-storage>=20.0.0",
        "azure-mgmt-monitor>=6.0.0",
        "azure-mgmt-costmanagement>=4.0.0",
        "azure-mgmt-recoveryservicesbackup>=4.1.0",
        "azure-mgmt-subscription>=3.1.1",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "rich>=12.0.0",
        "typer>=0.7.0",
    ],
    entry_points={
        "console_scripts": [
            "azure-orphan-detector=azure_orphan_detector.cli.main:main",
        ],
    },
    python_requires=">=3.8",
)