.PHONY: all pips
all: simple

simple: ../bin/buildout
	cd buildouts/simple && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/simple/bin/hatchdemo

# For comparing with pip/uv:
pips:
	uv run --with-requirements requirements/simple.txt hatchdemo
