from pathlib import Path
import sys

PROJECT_PATH = Path(__file__).parent.parent
SOURCE_PATH = PROJECT_PATH / 'src'
sys.path.append(str(SOURCE_PATH))
