from pathlib import Path
import logging
import sys
from dotenv import load_dotenv

from jinja2 import Environment, PackageLoader
###############################################################################
# Logging
###############################################################################
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
logger = logging.getLogger(__name__)

###############################################################################
# Files and paths.
###############################################################################
project_root = Path(__file__).parent.parent.parent

def resolve_file(name: str, relative_to: str = __file__):
    relative_to = Path(relative_to)

    if relative_to.is_file():
        return (relative_to.parent / name).resolve()
    else:
        return (relative_to / name).resolve()
    
###############################################################################
# Environment variables.
###############################################################################
# Load the .env file which contains the OpenAI API key.
load_dotenv(project_root / '.env')

###############################################################################
# Templating
###############################################################################
def default_template_env(module: str = 'stories', folder: str = 'templates') -> Environment:
    return Environment(
        loader=PackageLoader(module, folder)
    )

template_env = default_template_env()

def render_template(name: str, environment: Environment = template_env, **kwargs):
    return environment.get_template(name).render(**kwargs)
###############################################################################
