"""Print the runtimes used by the core experiment."""

import importlib.metadata
import json
import platform
from trace_xml_generalization import Worker

worker = Worker()
try:
    print(
        json.dumps(
            {
                "learner": platform.python_version(),
                "lark": importlib.metadata.version("lark-parser"),
                "oracle": worker.info,
            },
            indent=2,
        )
    )
finally:
    worker.close()
