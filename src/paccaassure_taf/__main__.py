"""``python -m paccaassure_taf`` — same as the ``pataf`` command.

Use this form where endpoint security blocks console-script launchers (``pataf.exe``).
"""

from paccaassure_taf.runner.cli import main

if __name__ == "__main__":
    main()
