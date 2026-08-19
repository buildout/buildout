.PHONY: all pips
all: simple namespaces

simple: ../bin/buildout
	cd buildouts/simple && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/simple/bin/hatchdemo
	buildouts/simple/bin/setuptoolsdemo

namespaces: ../bin/buildout
	cd buildouts/namespaces && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/namespaces/bin/ns_hat
	buildouts/namespaces/bin/ns_tools

# For comparing with pip/uv:
pips:
	uv run --with-requirements requirements/simple.txt hatchdemo
	uv run --with-requirements requirements/simple.txt setuptoolsdemo
	uv run --with-requirements requirements/namespaces.txt ns_hat
	uv run --with-requirements requirements/namespaces.txt ns_tools
