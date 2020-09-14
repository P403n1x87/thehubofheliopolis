# -*- coding: utf-8 -*-

import os
import shlex
import shutil
import sys
import datetime

from invoke import task
from invoke.main import program
from invoke.util import cd
from pelican import main as pelican_main
from pelican.server import ComplexHTTPRequestHandler, RootedHTTPServer
from pelican.settings import DEFAULT_CONFIG, get_settings_from_file

SETTINGS_FILE_BASE = "pelicanconf.py"
SETTINGS = {}
SETTINGS.update(DEFAULT_CONFIG)
LOCAL_SETTINGS = get_settings_from_file(SETTINGS_FILE_BASE)
SETTINGS.update(LOCAL_SETTINGS)

CONFIG = {
    "settings_base": SETTINGS_FILE_BASE,
    "settings_publish": "publishconf.py",
    # Output path. Can be absolute or relative to tasks.py. Default: 'output'
    "deploy_path": SETTINGS["OUTPUT_PATH"],
    # Github Pages configuration
    "github_pages_branch": "main",
    "commit_message": "'Publish site on {}'".format(datetime.date.today().isoformat()),
    # Host and port for `serve`
    "host": "localhost",
    "port": 8000,
}


def generate_redirects():
    # Generate redirects
    REDIRECTS = [
        (
            "python/profiling/2019/05/05/python-profiling.html",
            "deterministic-and-statistical-python-profiling.html",
        ),
        (
            "assembly/x86_64/2016/08/10/getting-started-with-x68-asm.html",
            "getting-started-with-x86-64-assembly-on-linux.html",
        ),
        (
            "number theory/algorithms/architecture/2017/03/06/primes.html",
            "prime-numbers-algorithms-and-computer-architectures.html",
        ),
        (
            "raspberry pi/iot/2017/07/31/intro-to-iot.html",
            "a-gentle-introduction-to-iot.html",
        ),
        (
            "android/java/gradle/2017/10/14/android-dev.html",
            "android-development-from-the-command-line.html",
        ),
        (
            "iot/websockets/asynchronous i/o/2018/03/03/websockets_asyncio.html",
            "iot-with-websockets-and-pythons-asyncio.html",
        ),
        (
            "python/assembly/2018/03/23/asm_python.html",
            "extending-python-with-assembly.html",
        ),
        ("linux/2018/08/04/containers.html", "what-actually-are-containers.html"),
    ]

    with open(os.path.join(LOCAL_SETTINGS["THEME"], "templates/redirect.html")) as fin:
        redirect_template = fin.read()
    for old, new in REDIRECTS:
        old_path = os.path.dirname(old)
        os.makedirs(os.path.join("output", old_path), exist_ok=True)
        with open(os.path.join("output", old), "w") as fout:
            fout.write(redirect_template.format(new=new))


@task
def clean(c):
    """Remove generated files"""
    if os.path.isdir(CONFIG["deploy_path"]):
        shutil.rmtree(CONFIG["deploy_path"])
        os.makedirs(CONFIG["deploy_path"])


@task
def build(c):
    """Build local version of site"""
    generate_redirects()
    pelican_run("-s {settings_base}".format(**CONFIG))


@task
def rebuild(c):
    """`build` with the delete switch"""
    pelican_run("-d -s {settings_base}".format(**CONFIG))


@task
def regenerate(c):
    """Automatically regenerate site upon file modification"""
    pelican_run("-r -s {settings_base}".format(**CONFIG))


@task
def serve(c):
    """Serve site at http://$HOST:$PORT/ (default is localhost:8000)"""

    class AddressReuseTCPServer(RootedHTTPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(
        CONFIG["deploy_path"],
        (CONFIG["host"], CONFIG["port"]),
        ComplexHTTPRequestHandler,
    )

    sys.stderr.write("Serving at {host}:{port} ...\n".format(**CONFIG))
    server.serve_forever()


@task
def serve_global(c):
    """Serve site at http://0.0.0.0:$PORT/"""

    class AddressReuseTCPServer(RootedHTTPServer):
        allow_reuse_address = True

    host = "0.0.0.0"

    server = AddressReuseTCPServer(
        CONFIG["deploy_path"], (host, CONFIG["port"]), ComplexHTTPRequestHandler
    )

    sys.stderr.write(
        "Serving at {host}:{port} ...\n".format(host=host, port=CONFIG["port"])
    )
    server.serve_forever()


@task
def reserve(c):
    """`build`, then `serve`"""
    build(c)
    serve(c)


@task
def preview(c):
    """Build production version of site"""
    pelican_run("-s {settings_publish}".format(**CONFIG))


@task
def livereload(c):
    """Automatically reload browser tab upon file modification."""
    from livereload import Server

    build(c)
    server = Server()
    # Watch the base settings file
    server.watch(CONFIG["settings_base"], lambda: build(c))
    # Watch content source files
    content_file_extensions = [".md", ".rst"]
    for extension in content_file_extensions:
        content_blob = "{0}/**/*{1}".format(SETTINGS["PATH"], extension)
        server.watch(content_blob, lambda: build(c))
    # Watch the theme's templates and static assets
    theme_path = SETTINGS["THEME"]
    server.watch("{}/templates/*.html".format(theme_path), lambda: build(c))
    static_file_extensions = [".css", ".js"]
    for extension in static_file_extensions:
        static_file = "{0}/static/**/*{1}".format(theme_path, extension)
        server.watch(static_file, lambda: build(c))
    # Serve output path on configured host and port
    server.serve(host=CONFIG["host"], port=CONFIG["port"], root=CONFIG["deploy_path"])


@task
def publish(c):
    """Publish to production via rsync"""
    pelican_run("-s {settings_publish}".format(**CONFIG))
    c.run(
        'rsync --delete --exclude ".DS_Store" -pthrvz -c '
        '-e "ssh -p {ssh_port}" '
        "{} {ssh_user}@{ssh_host}:{ssh_path}".format(
            CONFIG["deploy_path"].rstrip("/") + "/", **CONFIG
        )
    )


@task
def gh_pages(c):
    """Publish to GitHub Pages"""
    preview(c)
    c.run(
        "ghp-import -b {github_pages_branch} "
        "-m {commit_message} "
        "{deploy_path} -p".format(**CONFIG)
    )


def pelican_run(cmd):
    cmd += " " + program.core.remainder  # allows to pass-through args to pelican
    pelican_main(shlex.split(cmd))
