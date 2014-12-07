#!/bin/sh

# Tool that converts git content to srpm

WORKING_DIR=.
OUTPUT_DIR=.
GIT_HASH=master
DIST=f21
RESULT_FULL_PATH=true

usage() {
    echo "Usage: `basename $0` --git giturl [ --wd workdir ] [ --od outdir ]"
    echo " [ --hash githash ] [ --dist disttag ] [ --result-filename ]"
    exit 1
}

abort() {
    echo "Error: " "$1" >&2
    exit 1
}

while [ -n "$1" ] ; do
    case "$1" in
        --help)
            usage $0
            ;;
        --git)
            GIT_URL="$2"
            shift
            ;;
        --wd)
            WORKING_DIR="$2"
            shift
            ;;
        --od)
            OUTPUT_DIR="$2"
            shift
            ;;
        --hash)
            GIT_HASH="$2"
            shift
            ;;
        --dist)
            DIST="$2"
            shift
            ;;
        --result-filename)
            RESULT_FULL_PATH=false
            ;;
        *)
            usage
            ;;
    esac
    shift
done

if [ -z "$GIT_URL" ] ; then
    usage
fi

echo "Downloading from $GIT_URL and commit $GIT_HASH" >&2
echo "Output will be at $OUTPUT_DIR" >&2
echo "Using working dir $WORKING_DIR" >&2

mkdir -p $WORKING_DIR || abort "Could not create working dir '$WORKING_DIR', exiting."
mkdir -p $OUTPUT_DIR || abort "Could not create output dir '$OUTPUT_DIR', exiting."

GIT_DIR=$(mktemp -d "$WORKING_DIR/gitXXXXXXXX")
git clone "$GIT_URL" "$GIT_DIR" >&2 || abort "Could not clone git repo '$GIT_URL' to dir '$GIT_DIR'"

pushd "$GIT_DIR" &>/dev/null
git checkout "$GIT_HASH" >&2 || abort "Could not checkout 'GIT_HASH'"

touch sources || abort "Could not touch 'sources' file"
fedpkg --dist "$DIST" srpm | tee srpmbuild.log >&2

srpm=$(cat srpmbuild.log | grep -e '^Wrote: ' | sed -e 's/Wrote: //')
srpmname=$(basename $srpm)

popd &>/dev/null

mv "$srpm" "$OUTPUT_DIR"

$RESULT_FULL_PATH && output="$OUTPUT_DIR/$srpmname" || output="$srpmname"
echo "{\"result\": 1, \"srpm\": \"$output\"}"

