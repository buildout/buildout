try:
    # support pip>=19.0
    from pip._internal.cli.main import main
    pip_install_cmd = (
        'from pip._internal.cli.main import main; sys.exit(main())'
    )
except ImportError:
    # support pip>=10.0
    from pip._internal import main
    pip_install_cmd = 'from pip._internal import main; sys.exit(main())'
