#!/bin/bash

# Studsvik CMS calculator script for fz: runs CASMO5, CMSLINK5 or SIMULATE5 and checks the result.
# Usage: CMS.sh <cas5|cmslink5|sim5> <input_file or input_directory>
#
# Environment:
#   CMSHOME          CMS installation directory (contains bin/cas5, bin/cmslink5, bin/sim5)
#   LM_LICENSE_FILE  FlexNet license server of the Studsvik codes (e.g. port@server)
#   CMS_DATA_PATH    optional, colon-separated directories searched for the data files named in the
#                    input (*.lib, *.cax, *.res, or the same .gz, decompressed) and missing from the
#                    case directory; default: the install_inputs directories of SIMULATE5 and
#                    CMSLINK5 under $CMSHOME
#
# The CMS wrappers always return 0, even after a fatal error: this script reads the termination
# banner instead and exits 1 (first fatal messages on stderr) when the run did not end normally.

EXE="$1"
shift
case "$EXE" in
  cas5|cmslink5|sim5) ;;
  *) echo "Usage: $0 <cas5|cmslink5|sim5> <input_file or input_directory>" >&2; exit 2 ;;
esac

# Check if CMSHOME is set
if [ -z "$CMSHOME" ]; then
  echo "Error: CMSHOME environment variable is not set" >&2
  echo "Please set CMSHOME to your Studsvik CMS installation directory" >&2
  echo "Example: export CMSHOME=/opt/studsvik/CMSCODES" >&2
  exit 1
fi

# Check if the code wrapper exists
if [ ! -x "$CMSHOME/bin/$EXE" ]; then
  echo "Error: $EXE not found at $CMSHOME/bin/$EXE" >&2
  exit 1
fi
if [ -z "$LM_LICENSE_FILE" ]; then
  echo "Warning: LM_LICENSE_FILE is not set (license server of the CMS codes)" >&2
fi
export PATH="$CMSHOME/bin:$PATH"

# Never prompt nor write-protect the outputs (the wrappers do both by default)
export CMS_PROMPT=no CMS_PROTECT=no CMS_KILL=yes

# If directory as input, cd into it
if [ -d "$1" ]; then
  cd "$1"
  INP=`ls *.inp 2>/dev/null | head -n 1`
  if [ -z "$INP" ]; then
    INP=`ls * 2>/dev/null | grep -v '\.out$\|\.log$\|\.cax$\|\.lib$\|\.res$\|\.sum$\|\.txt$\|^PID$' | head -n 1`
  fi
  shift
# If $* are files, find the input file (first *.inp, else the first file)
elif [ $# -gt 0 ]; then
  INP=""
  for f in "$@"; do
    if [ -f "$f" ] && [ "${f%.inp}" != "$f" ]; then INP="$f"; break; fi
  done
  if [ -z "$INP" ]; then
    for f in "$@"; do
      if [ -f "$f" ]; then INP="$f"; break; fi
    done
  fi
  shift $#
else
  echo "Usage: $0 <cas5|cmslink5|sim5> <input_file or input_directory>" >&2
  exit 2
fi
if [ -z "$INP" ] || [ ! -f "$INP" ]; then
  echo "No input file found. Exiting." >&2
  exit 1
fi
cd "$(dirname "$INP")"
INP="$(basename "$INP")"

# The CMS wrappers require the .inp extension
BASE="${INP%.*}"
if [ "$INP" != "$BASE.inp" ]; then
  cp -f "$INP" "$BASE.inp"
fi
INP="$BASE.inp"

# Data files named in the input (quoted *.lib / *.cax / *.res), except the library a CMSLINK5
# input creates on its 'NEW' card: symlink them from CMS_DATA_PATH when absent
DATA_PATH="${CMS_DATA_PATH:-$(ls -d "$CMSHOME"/S5/v*/install_inputs 2>/dev/null | sort -V | tail -n 1):$(ls -d "$CMSHOME"/CLNK5/v*/install_inputs 2>/dev/null | sort -V | tail -n 1)}"
for f in `grep -viE "^\s*'NEW'" "$INP" | grep -oE "'[^' ]+\.(lib|cax|res)'" | tr -d "'" | sort -u`; do
  if [ -e "$f" ] || [ "${f#*/}" != "$f" ]; then continue; fi
  IFS=: read -ra dirs <<< "$DATA_PATH"
  for d in "${dirs[@]}"; do
    if [ -n "$d" ] && [ -e "$d/$f" ]; then ln -sf "$d/$f" "$f"; break; fi
    if [ -n "$d" ] && [ -e "$d/$f.gz" ]; then gunzip -c "$d/$f.gz" > "$f"; break; fi
  done
  if [ ! -e "$f" ]; then
    echo "Warning: data file $f not found in the case directory nor in CMS_DATA_PATH" >&2
  fi
done

# Store process ID for tracking
echo $$ >> PID

# Run the code (screen output goes to stdout)
"$CMSHOME/bin/$EXE" "$INP" < /dev/null &
PID_CMS=$!
echo $PID_CMS >> PID
wait $PID_CMS

# Clean up PID file
if [ -f "PID" ]; then
  rm -f "PID"
fi

# Check the termination banner (the exit code of the wrappers is always 0)
case "$EXE" in
  cas5)
    grep -q "Normal Termination" "$BASE.log" 2>/dev/null && exit 0
    MSG=`grep -h "\[Fatal Error\]" "$BASE.log" 2>/dev/null | head -n 3` ;;
  cmslink5)
    grep -q "NORMAL TERMINATION" "$BASE.out" 2>/dev/null && ! grep -q "RUN ABORTED" "$BASE.out" && exit 0
    MSG=`grep -h " FATAL " "$BASE.out" 2>/dev/null | head -n 3` ;;
  sim5)
    grep -q "Normal Termination" "$BASE.out" 2>/dev/null && exit 0
    MSG=`grep -h " FATAL " "$BASE.out" 2>/dev/null | head -n 3` ;;
esac
echo "Error: $EXE did not terminate normally ($INP)" >&2
if [ -n "$MSG" ]; then
  echo "$MSG" | sed 's/^ *//; s/  */ /g' >&2
else
  echo "No fatal message found: check license (LM_LICENSE_FILE) and the screen output" >&2
fi
exit 1
