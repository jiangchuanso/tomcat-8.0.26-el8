#!/bin/sh
# Tomcat 启动环境补充（由 RPM 安装到 /opt/tomcat8/bin/setenv.sh）
# 作用：兜底补充 JVM 的 java.library.path。本包为纯 Java noarch（默认 NIO + JSSE），
#       运行不依赖 tomcat-native / APR 原生库；若未来启用原生库，本文件仍能
#       保证标准库搜索路径可用，且不覆盖用户已自行指定的 java.library.path。

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
