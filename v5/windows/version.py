"""Single source of Windows release identity; macOS version is independent."""
from schoolnet import __release_version__
VERSION = __release_version__
FILE_VERSION = '5.0.0.11'
LABEL = f'MINER ALPHA v{VERSION} · Windows'
TAG = 'miner-alpha-v' + VERSION
STEM = f'MINER-ALPHA-v{VERSION}-Windows-x64'
