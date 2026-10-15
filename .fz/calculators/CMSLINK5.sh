#!/bin/bash

# CMSLINK5 calculator script for fz (see CMS.sh)
exec bash "$(dirname "$0")/CMS.sh" cmslink5 "$@"
