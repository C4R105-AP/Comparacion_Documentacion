from __future__ import annotations

import multiprocessing

from wi_compare.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
