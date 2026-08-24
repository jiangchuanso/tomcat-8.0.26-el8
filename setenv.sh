#!/bin/sh
# Tomcat 启动环境补充（由 RPM 安装到 /opt/tomcat8/bin/setenv.sh）
# 作用：确保 JVM 能找到 libtcnative-1.so（APR 原生库）。
# 说明：64 位 JDK 默认 java.library.path 已含 /usr/lib64，本文件仅作跨架构兜底，
#       且不覆盖用户已自行指定的 java.library.path。

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)  JAVA_ARCH=amd64   ;;
    aarch64) JAVA_ARCH=aarch64 ;;
    *)       JAVA_ARCH="$ARCH" ;;
esac

# 重新组装一份“标准目录 + 兜底目录”的库搜索路径
LIBPATH="/usr/lib64:/lib64:/usr/lib:/lib"
LIBPATH="$LIBPATH:/usr/java/packages/lib/${JAVA_ARCH}"
if [ -n "${JAVA_HOME:-}" ]; then
    LIBPATH="$LIBPATH:${JAVA_HOME}/jre/lib/${JAVA_ARCH}:${JAVA_HOME}/lib/${JAVA_ARCH}"
fi

# 仅在用户未自行指定 java.library.path 时追加，避免覆盖既有配置
case " ${JAVA_OPTS} " in
    *"java.library.path"*) ;;
    *) JAVA_OPTS="$JAVA_OPTS -Djava.library.path=$LIBPATH" ;;
esac
