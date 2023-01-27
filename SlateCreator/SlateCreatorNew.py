import os
import re
import logging
import subprocess
import json
import platform
import opentimelineio as otio
from html2image import Html2Image

class SlateCreator:
    def __init__(self, logger=None, data=dict()):
        self.template_path = ""
        self.resources_path = ""
        self._template_string = ""
        self._template_string_computed = ""
        self.log = logger or logging.getLogger("SlateCreator")
        self.data = data
        self.fps = float(24)
        self.start_frame = int(1001)
        self._html_thumb_match_regex = re.compile(
            r"{thumbnail(.*?)}"
        )
        self._html_optional_match_regex = re.compile(
            r"{(.*?)_optional}"
        )
        self._html_path_match_regex = re.compile(
            r"src=\"(.*?)\"|href=\"(.*?)\"|{(thumbnail.*?)}"
        )
        self._html_comment_open_regex = re.compile(
            r"<!--(.*?)"
        )
        self._html_comment_close_regex = re.compile(
            r"(.*?)-->"
        )

    def _run(self, cmd):
        res = subprocess.run(cmd, shell=True,
            check=True, capture_output=True)
        return res

    def read_template(self):
        """
        Reads template from file and normalizes/absolutizes
        any relative paths in html. The paths gets expanded with
        the resources directory as base. Stores template in an
        internal var for further use.
        """

        if not self.template_path:
            raise ValueError("Please Specify a template path!")
        if not self.template_res_path:
            raise ValueError("Please Specify a resources path!")

        with open(self.template_path, 'r') as t:
            template = t.readlines()

        template_computed = []
        html_comment_open = False
        
        for line in template:
            
            if self._html_comment_open_regex.search(line) is not None:
                html_comment_open = True
            
            if self._html_comment_close_regex.search(line) is not None:
                html_comment_open = False
                continue
            
            if html_comment_open:
                continue
            
            search = self._html_path_match_regex.search(line)
            
            if search is not None:
                
                path_tuple = self._html_path_match_regex.findall(line)[0]
                path = ""
                
                for element in path_tuple:
                    if element:
                        path = element
                        break
                
                if not path.find("{"):
                    template_computed.append(line)
                    continue

                base, file = os.path.split(path)
                
                if self.template_res_path:
                    path_computed = os.path.normpath(
                        os.path.join(
                            self.template_res_path,
                            file
                        )
                    )
                else:
                    path_computed = os.path.normpath(
                        file
                    )
                
                template_computed.append(
                    line.replace(path, path_computed)
                )
            else:
                template_computed.append(line)
        
        template = "".join(template_computed)
        
        self._template_string = template
        
        self.log.debug("Template string: '{}'".format(template))

    def compute_template(
        self,
        process_optionals=True
    ):
        """
        Computes template by substituting template strings.
        Needs keys to be at the root of data dict, no support
        for nested dicts for now, just for lists.
        Keys in template with "_optional" are substituted
        with "display:None" in the style property, this
        enables to hide selectively any block if any
        corresponding key is empty.
        example: {scope} -> {scope_optional} 
        """

        if not self._template_string:
            raise ValueError(
                "Slate Template data is empty, please " + 
                "reread template or check source file."
            )
        
        if process_optionals:
            
            hidden_string = "style=\"display:None;\""

            optional_matches = self._html_optional_match_regex.findall(
                self._template_string
            )

            for m in optional_matches:
                self.data["{}_optional".format(m)] = ""
                if not self.data[m]:
                    self.data["{}_optional".format(m)] = hidden_string
        
        try:
            self._template_string_computed = self._template_string.format_map(
                self.data
            )
            self.log.debug("Computed Template string: '{}'".format(
                self._template_string_computed
            ))
        except KeyError as err:
            msg = "Missing {} Key in instance data. ".format(err)
            msg += "Template formatting cannot be completed successfully!"
            self.log.error(msg)
            self._template_string_computed = self._template_string
            raise

    def get_timecode(self, input):
        """
        Find timecode using oiio, fallback to ffprobe
        for movie files. If no TC is found constructs a tc
        with the start_frame class parameter
        """
        tc = self.frames_to_timecode(self.start_frame, self.fps)

        cmd = ["iinfo", "-v", input]
        res = self._run(cmd)
        output = res.stdout.decode("utf-8").splitlines()
        for line in output:
            if "TimeCode" in line:
                tc = line.split(" ")[-1]

        cmd = ["ffprobe", "-loglevel", "verbose", "-select_streams",
            "v:0", "-show_streams", "-of", "json", input]
        res = self._run(cmd)
        output = json.loads(
            res.stdout.decode("utf-8"))["streams"][0]
        if output.get("tags"):
            if output["tags"].get("timecode"):
                tc = output["tags"]["timecode"]

        self.data["timecode"] = tc
        return {
            "timecode": tc
        }

    def get_resolution(self, input):
        """
        Find input resolution using ffprobe.
        """
        cmd = ["ffprobe", "-loglevel", "verbose", "-select_streams",
            "v:0", "-show_streams", "-of", "json", input]
        res = self._run(cmd)

        output = json.loads(
            res.stdout.decode("utf-8"))["streams"][0]
        self.data["resolution_width"] = output["width"]
        self.data["resolution_height"] = output["height"]
        return {
            "resolution_width": output["width"],
            "resolution_height": output["height"]
        }

    def timecode_to_frames(self, timecode, framerate):
        rt = otio.opentime.from_timecode(timecode, framerate)
        return int(otio.opentime.to_frames(rt))

    def frames_to_timecode(self, frames, framerate):
        rt = otio.opentime.from_frames(frames, framerate)
        return otio.opentime.to_timecode(rt)

    def frames_to_seconds(self, frames, framerate):
        rt = otio.opentime.from_frames(frames, framerate)
        return otio.opentime.to_seconds(rt)

    def render_image_oiio(self, input, output,
        in_args=list(), out_args=list()):
        """
        renders any image using a subprocess command. args is a list
        of strings returns the completed supprocess
        """
        cmd = ["oiiotool", in_args, "-i", input, out_args, "-o", output]
        res = self._run(cmd)

        return res

    def render_thumbnail(self, input):
        pass

    def render_slate(self, output):
        """
        Renders out the slate. Templates are rendered using
        Screen color space, usually Rec.709 or sRGB. Any
        HTML that needs to respect color needs to take that
        into account.
        """

        data_width = self.data["resolution_width"] or 1920
        data_height = self.data["resolution_height"] or 1080

        if not resolution:
            resolution = (data_width, data_height)
        else:
            self.data["resolution_width"] = resolution[0]
            self.data["resolution_height"] = resolution[1]

        self.compute_template() 

        htimg = Html2Image(
            output_path=os.path.dirname(output))

        slate_rendered_path = htimg.screenshot(
            html_str=self._template_string_computed,
            save_as=os.path.basename(output), size=resolution)

        return slate_rendered_path

    def create_slate(self, input, output):
        self.get_resolution(input)
        self.get_timecode(input)
        self.read_template()
        self.compute_template()
        self.render_slate(output)






input = [
    "C:/Users/22DOGS/a.exr"
]

paths = [
    "R:\\_pipeline\\OpenPype\\3.14\\vendor\\bin\\ffmpeg\windows\\bin",
    "R:\\_pipeline\\OpenPype\\3.14\\vendor\\bin\\oiio\\windows"
]

for p in paths:
    os.environ["PATH"] += os.pathsep + p

sc = SlateCreator()

sc.get_timecode(input[0])
sc.get_resolution(input[0])

sc.render_image_oiio(input[0], "C:/Users/22DOGS/slate.png")
