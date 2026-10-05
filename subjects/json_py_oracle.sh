#!/bin/sh
python3 -c "import sys,json; json.loads(open(sys.argv[1],'rb').read().decode('utf-8','surrogateescape'))" "$1" 2>/dev/null
