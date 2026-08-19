.PHONY: all clean simple namespaces downloads final mixed pips
all: simple namespaces final mixed

clean:
	# Remove files and directories that are ignored by git.
	git clean -dfX

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

DOWNLOADS_SENTINEL=downloads/.sentinel
$(DOWNLOADS_SENTINEL): packages/hatchdemo/pyproject.toml packages/setuptoolsdemo/pyproject.toml packages/ns.hat/pyproject.toml packages/ns.tools/pyproject.toml
	rm -rf downloads/dist
	mkdir -p downloads/dist
	uvx --from build pyproject-build --wheel --outdir downloads/dist packages/hatchdemo
	uvx --from build pyproject-build --wheel --outdir downloads/dist packages/setuptoolsdemo
	uvx --from build pyproject-build --wheel --outdir downloads/dist packages/ns.hat
	uvx --from build pyproject-build --wheel --outdir downloads/dist packages/ns.tools
	@touch $(DOWNLOADS_SENTINEL)

downloads: $(DOWNLOADS_SENTINEL)
	ls -l downloads/dist

final: ../bin/buildout downloads
	cd buildouts/final && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/final/bin/hatchdemo
	buildouts/final/bin/setuptoolsdemo
	buildouts/final/bin/ns_hat
	buildouts/final/bin/ns_tools

mixed: ../bin/buildout downloads
	cd buildouts/mixed && ../../../bin/buildout
	@echo "Buildout has finished. Running the scripts."
	buildouts/mixed/bin/ns_hat
	buildouts/mixed/bin/ns_tools

# For comparing with pip/uv:
pips:
	uv run --with-requirements requirements/simple.txt hatchdemo
	uv run --with-requirements requirements/simple.txt setuptoolsdemo
	uv run --with-requirements requirements/namespaces.txt ns_hat
	uv run --with-requirements requirements/namespaces.txt ns_tools
	uv run --with-requirements requirements/final.txt hatchdemo
	uv run --with-requirements requirements/final.txt setuptoolsdemo
	uv run --with-requirements requirements/final.txt ns_hat
	uv run --with-requirements requirements/final.txt ns_tools
