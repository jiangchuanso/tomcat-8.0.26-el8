#!/bin/sh
# 追加usr/lib64
JAVA_OPTS="$JAVA_OPTS -Djava.library.path=/usr/java/packages/lib/aarch64:/lib:/usr/lib:/usr/lib64"