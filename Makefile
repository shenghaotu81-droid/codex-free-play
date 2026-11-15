.PHONY: demo test build

demo:
	python3 -m ferry demo

test:
	python3 -m unittest discover -s tests -v

build:
	python3 scripts/build_zipapp.py
