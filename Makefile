.PHONY: demo test build ferry-test

demo:
	python3 run.py ferry demo

test: ferry-test
	cd projects/exchange-sim && python3 -m unittest discover -s tests -v

ferry-test:
	cd projects/ferry && python3 -m unittest discover -s tests -v
	cd projects/ferry && python3 tests/terminal_smoke.py

build:
	python3 projects/ferry/scripts/build_zipapp.py
