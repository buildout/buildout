Test maintenance: test with pip 26.1.2, updated GitHub workflow action
versions, fixed script tests and Windows detection in ``prepare.sh``,
restored the propagate flags of ``zc.buildout*`` loggers after each pytest
so later ``caplog`` captures are not starved, and made the test harness's
index URLs, file server and output normalizers Windows- and uv-proof.
[maurits, gotcha]
