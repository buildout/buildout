.PHONY: all pips
all: simple

simple: ../bin/buildout
	cd buildouts/simple && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/simple/bin/hatchdemo
	buildouts/simple/bin/setuptoolsdemo

# For comparing with pip/uv:
pips:
	uv run --with-requirements requirements/simple.txt hatchdemo
	uv run --with-requirements requirements/simple.txt setuptoolsdemo
