"""Build static HTML site from directory of HTML templates and plain files."""
import shutil
import pathlib
import os
import json
import sys
import jinja2
import click


@click.command()
@click.argument('input_dir', type=click.Path(exists=True, readable=True))
@click.option('--output', '-o', help='Output directory.', type=click.Path())
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    show_default=True,
    default=False,
    help='Print more output.')
def main(input_dir, output, verbose):
    """Templated static website generator."""
    default_check = False

    if output is None:
        default_check = True
        output = input_dir
    # output mode on
    input_dir = pathlib.Path(input_dir)

    output = pathlib.Path(output)

    if default_check is True:
        output = output/"html"

        if os.path.exists(output):
            print("already exists, skipping")
            sys.exit(1)

    os.makedirs(output)

    if os.path.exists(input_dir/"static") is True:
        scr = input_dir/"static"
        shutil.copytree(scr, output, dirs_exist_ok=True)
        if verbose is True:
            print("Copied", input_dir/"static ->", output)

    try:
        with open(input_dir/"config.json", "r", encoding="utf-8") as f_p:
            res = json.load(f_p)
            f_p.close()
    except json.JSONDecodeError:
        print("some error in json")

    template_dir = input_dir/"templates"
    try:
        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
        )

        for element in res:
            content = element["context"]
            template = template_env.get_template(element["template"])
            template = template.render(content)
            url = element["url"].lstrip("/")
            outputpath = output/url/"index.html"
            if not os.path.exists(output/url):
                os.makedirs(output/url)

            print("Rendered", element["template"], "->", outputpath)

            with open(outputpath, 'w', encoding="utf-8") as f_h:
                f_h.write(template)

    except jinja2.TemplateError(message=None):
        print("some error in jinja")


if __name__ == "__main__":
    main()
