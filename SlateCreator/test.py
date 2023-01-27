import os
import subprocess
import json

input = "C:/Users/22DOGS/a.exr"

tc = "00:00:00:00"

env = {
    "PATH": "R:\\_pipeline\\OpenPype\\3.14\\vendor\\bin\\ffmpeg\windows\\bin;R:\\_pipeline\\OpenPype\\3.14\\vendor\\bin\\oiio\\windows"
}

def get_timecode(input, env=env, frame=1001):

    #tc = frame

    cmd = ["iinfo", "-v", input]

    res = subprocess.run(cmd, env=env, shell=True,
        check=True, capture_output=True)

    output = res.stdout.decode("utf-8").splitlines()

    for line in output:
        if "TimeCode" in line:
            tc = line.split(" ")[-1]

    cmd = ["ffprobe", "-loglevel", "verbose", "-select_streams",
        "v:0", "-show_streams", "-of", "json", input]

    res = subprocess.run(cmd, env=env, shell=True,
        check=True, capture_output=True)

    output = json.loads(
        res.stdout.decode("utf-8"))["streams"][0]

    print(json.dumps(output, indent=4, default=str))

    if output.get("tags"):
        if output["tags"].get("timecode"):
            tc = output["tags"]["timecode"]

    return tc

get_timecode(input)