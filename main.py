import os
import logging
import json
from SlateCreator.SlateCreator import SlateCreator


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("SlateCreator")

current_dir = os.path.dirname(os.path.realpath(__file__))

data_file = os.path.normpath(
    os.path.join(
        current_dir,
        "data",
        "mock_data.json",
    )
)

template_file = os.path.normpath(
    os.path.join(
        current_dir,
        "templates",
        "generic_slate",
        "generic_slate.html"
    )
)

resources_dir = os.path.normpath(
    os.path.join(
        current_dir,
        "templates",
        "generic_slate",
        "resources"
    )
)

staging_dir = os.path.normpath(
    os.path.join(
        current_dir,
        "staging"
    )
)

oiio_dir = os.path.normpath(
    os.path.join(
        current_dir,
        "vendor/oiio/windows"
    )
)

ffmpeg_dir = os.path.normpath(
    os.path.join(
        current_dir,
        "vendor/ffmpeg/windows/bin"
    )
)

thumbnail_file = os.path.normpath(
    os.path.join(
        resources_dir,
        "thumbnail_placeholder.jpg"
    )
)

slate_env = {
    "PATH": oiio_dir + os.pathsep + ffmpeg_dir
}

data = {}
with open("data/mock_data.json", "r") as f:
    data = json.loads(f.read())

data["thumbnail"] = thumbnail_file

slate = SlateCreator(
    template_path=template_file,
    resources_path=resources_dir,
    log=log,
    env=slate_env,
    data=data,
    staging_dir=staging_dir
)

slate.set_resolution(1920,1080)
slate.render_slate()