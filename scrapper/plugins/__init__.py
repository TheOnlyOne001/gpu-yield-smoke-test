"""
GPU pricing plugins for various cloud providers.
"""

# Import all plugin modules
try:
    from . import runpod
except ImportError as e:
    print(f"Warning: Failed to import runpod plugin: {e}")
    runpod = None

try:
    from . import akash
except ImportError as e:
    print(f"Warning: Failed to import akash plugin: {e}")
    akash = None

try:
    from . import aws_spot
except ImportError as e:
    print(f"Warning: Failed to import aws_spot plugin: {e}")
    aws_spot = None

try:
    from . import vast_ai
except ImportError as e:
    print(f"Warning: Failed to import vast_ai plugin: {e}")
    vast_ai = None

try:
    from . import io_net
except ImportError as e:
    print(f"Warning: Failed to import io_net plugin: {e}")
    io_net = None

# Export available plugins
__all__ = []

# Add available plugins to exports
if runpod:
    __all__.append('runpod')
if akash:
    __all__.append('akash')
if aws_spot:
    __all__.append('aws_spot')
if vast_ai:
    __all__.append('vast_ai')
if io_net:
    __all__.append('io_net')

# Create a registry of available plugins
AVAILABLE_PLUGINS = {}

if runpod:
    AVAILABLE_PLUGINS['runpod'] = runpod
if akash:
    AVAILABLE_PLUGINS['akash'] = akash
if aws_spot:
    AVAILABLE_PLUGINS['aws_spot'] = aws_spot
if vast_ai:
    AVAILABLE_PLUGINS['vast_ai'] = vast_ai
if io_net:
    AVAILABLE_PLUGINS['io_net'] = io_net