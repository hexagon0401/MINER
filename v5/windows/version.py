"""Single source of Windows release identity; macOS version is independent."""
from schoolnet import __release_version__, __preview_revision__
VERSION = __release_version__
FILE_VERSION = '5.0.0.15'
LABEL = f'MINER STRATA v{VERSION} Preview {__preview_revision__} · Windows'
TAG = f'miner-strata-v{VERSION}-preview.{__preview_revision__}'
STEM = f'MINER-STRATA-v{VERSION}-preview.{__preview_revision__}-Windows-x64'
