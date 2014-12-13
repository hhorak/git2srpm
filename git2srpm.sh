#!/bin/sh

# Tool that converts git content to srpm

WORKING_DIR=.
OUTPUT_DIR=.
GIT_HASH=master
DIST=".fc21"
RESULT_FULL_PATH=true
SCRIPTS_PATH=$(readlink -f `dirname $0`)
RETENTION_COUNT_SRPM=20
RETENTION_COUNT_WD=5

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

# applying retention policy
# remove all but $RETENTION_COUNT_WD last working dirs
pushd $WORKING_DIR >/dev/null
ls -ct | tail -n +$RETENTION_COUNT_WD | xargs rm -rf
popd >/dev/null
# remove all but $RETENTION_COUNT_SRPM last srpms dirs
pushd $OUTPUT_DIR >/dev/null
ls -ct | tail -n +$RETENTION_COUNT_SRPM | xargs rm -rf
popd >/dev/null

GIT_DIR=$(mktemp -d "$WORKING_DIR/gitXXXXXXXX")
git clone "$GIT_URL" "$GIT_DIR" >&2 || abort "Could not clone git repo '$GIT_URL' to dir '$GIT_DIR'"

pushd "$GIT_DIR" &>/dev/null
git checkout "$GIT_HASH" >&2 || abort "Could not checkout 'GIT_HASH'"

touch sources || abort "Could not touch 'sources' file"

# This should do the same as
# fedpkg --dist "$DIST" srpm | tee srpmbuild.log >&2
$SCRIPTS_PATH/getsource.py | tee srpmbuild.log >&2
specfile=$(ls *.spec | head -n 1)
# hack with changing HOME so the rpmbuild sees .rpmmacros file
# in the scripts directory
HOME=$SCRIPTS_PATH \
/usr/bin/rpmbuild -bs --define '_sourcedir .' \
                      --define '_specdir .' \
                      --define '_srcrpmdir .' \
                      --define "dist $DIST" \
                      --define '_builddir .' \
                      --define '_rpmdir .' \
                      --define '_topdir .' \
                      --define '_buildrootdir .' \
                      "$specfile"  | tee srpmbuild2.log >&2

srpm=$(cat srpmbuild2.log | grep -e '^Wrote: ' | sed -e 's/Wrote: //')
srpm=$(readlink -f "$srpm")
srpmname=$(basename "$srpm")

popd &>/dev/null

mv "$srpm" "$OUTPUT_DIR"

$RESULT_FULL_PATH && output="$OUTPUT_DIR/$srpmname" || output="$srpmname"
echo "{\"result\": 1, \"srpm\": \"$output\"}"

