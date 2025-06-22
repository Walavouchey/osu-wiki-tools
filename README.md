# osu! wiki tools

A collection of various tools that may be useful for [osu! wiki](https://osu.ppy.sh/wiki/) contributors

## Installation

```sh
pip install osu-wiki-tools
```

## Testing

### Setup

Install Python C API headers (required for building the `pynput` dependency):

```sh
apt install python3-dev
```

Create the virtual enviroment:

```sh
python3 -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```

### Headless tests

```sh
pytest --mypy
```

### Visual tests

```sh
./run_visual_tests.py
```
