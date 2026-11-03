#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -z "${JAVA_HOME:-}" ] && [ -d .tools/jdk-17.0.21+9/Contents/Home ]; then
    export JAVA_HOME="$PWD/.tools/jdk-17.0.21+9/Contents/Home"
fi
if [ ! -d "${ANDROID_HOME:-/nonexistent}/platforms" ] && [ -d .tools/android-sdk/platforms ]; then
    export ANDROID_HOME="$PWD/.tools/android-sdk"
fi
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$PWD/.tools/gradle-cache}"
python3 tools/prepare_suite.py
python3 tools/prepare_play_metadata.py
if [ "$#" -eq 0 ]; then set -- assembleSideloadDebug lintSideloadDebug; fi
if [ -x .tools/gradle-9.3.1/bin/gradle ]; then
    exec .tools/gradle-9.3.1/bin/gradle --no-daemon "$@"
fi
exec ./gradlew --no-daemon "$@"
