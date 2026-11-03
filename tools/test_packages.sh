#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
task_jdk="${JAVA_HOME:-$PWD/.tools/jdk-17.0.21+9/Contents/Home}"
mkdir -p .tools/package-tests
"$task_jdk/bin/javac" -d .tools/package-tests app/src/main/java/org/wordcraft/offline/PackArchive.java tools/testsrc/org/wordcraft/offline/PackArchiveTest.java
"$task_jdk/bin/java" -cp .tools/package-tests org.wordcraft.offline.PackArchiveTest vendor/*-web-*.zip
