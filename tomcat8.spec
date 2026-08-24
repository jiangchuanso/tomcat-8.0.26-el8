Name:           tomcat8
Version:        8.0.26
Release:        2%{?dist}
Summary:        Apache Tomcat 8 Servlet/JSP Container

License:        Apache-2.0
URL:            https://tomcat.apache.org/
Source0:        apache-tomcat-%{version}.tar.gz
Source1:        setenv.sh

# jsvc（commons-daemon）编译依赖：C 工具链 + JDK（提供 jni.h 与 javac）
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  java-1.8.0-openjdk-devel
Requires:       java-headless >= 1:1.8.0

# 主包为纯 Java 运行时，标记为 noarch
BuildArch:      noarch
# 原生子包仅提供 jsvc（特权端口降权），设为弱依赖，可按需安装
Recommends:     tomcat8-native = %{version}-%{release}

%description
Apache Tomcat is an open source implementation of the Java Servlet and
JavaServer Pages technologies.

# 原生子包：仅包含按架构编译的 jsvc（x86_64 / aarch64）
%package native
Summary:        Tomcat 8 jsvc (commons-daemon) native binary
%description native
Architecture-specific native component for Tomcat 8:
- jsvc  (commons-daemon，用于以特权端口启动后降权；APR/native TLS 未启用)

%prep
%setup -q -n apache-tomcat-%{version}

%build
# 探测 JAVA_HOME（容器内为 java-1.8.0-openjdk-devel，提供 jni.h 与 javac）
export JAVA_HOME=$(ls -d /usr/lib/jvm/java-1.8.0-openjdk 2>/dev/null | head -1)
if [ -z "$JAVA_HOME" ]; then
    JAVA_HOME=$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")
fi
export JAVA_HOME

# 编译 commons-daemon (jsvc)
tar xzf bin/commons-daemon-native.tar.gz
pushd commons-daemon-*/unix
./configure --with-java="$JAVA_HOME"
make
popd

%install
rm -rf %{buildroot}

# 安装 Tomcat 到 /opt/tomcat8
mkdir -p %{buildroot}/opt/tomcat8
cp -R * %{buildroot}/opt/tomcat8

# 移除仅用于编译的源码包与解压目录（不进入最终包）
rm -f  %{buildroot}/opt/tomcat8/bin/commons-daemon-native.tar.gz
rm -f  %{buildroot}/opt/tomcat8/bin/tomcat-native.tar.gz
rm -rf %{buildroot}/opt/tomcat8/commons-daemon-*
rm -rf %{buildroot}/opt/tomcat8/tomcat-native-*

# 运行时目录
mkdir -p %{buildroot}/var/log/tomcat8
mkdir -p %{buildroot}/var/cache/tomcat8/{temp,work}
mv %{buildroot}/opt/tomcat8/conf %{buildroot}/opt/tomcat8/conf.dist
touch %{buildroot}/var/cache/tomcat8/tomcat8.pid

# 安装自定义 setenv.sh（JVM 启动环境变量兜底）
install -m 0644 %{SOURCE1} %{buildroot}/opt/tomcat8/bin/setenv.sh

# jsvc 装入 libexec，避免污染 PATH（native 子包）
mkdir -p %{buildroot}%{_libexecdir}/tomcat8
install -m 0755 commons-daemon-*/unix/jsvc %{buildroot}%{_libexecdir}/tomcat8/jsvc

# 创建 systemd 服务文件
mkdir -p %{buildroot}/usr/lib/systemd/system
cat > %{buildroot}/usr/lib/systemd/system/tomcat8.service <<EOF
[Unit]
Description=Apache Tomcat 8
After=syslog.target network.target

[Service]
Type=forking
User=tomcat
Group=tomcat

Environment=CATALINA_HOME=/opt/tomcat8
Environment=CATALINA_BASE=/opt/tomcat8
Environment=CATALINA_PID=/var/cache/tomcat8/tomcat8.pid

ExecStart=/opt/tomcat8/bin/startup.sh
ExecStop=/opt/tomcat8/bin/shutdown.sh

LimitNOFILE=65536
LimitNPROC=4096

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

%clean
rm -rf %{buildroot}

%post
# 创建系统用户和组
if ! id tomcat &>/dev/null; then
    groupadd -r tomcat
    useradd -r -s /sbin/nologin -d /opt/tomcat8 -g tomcat tomcat
fi

# 设置目录权限
chown -R tomcat:tomcat /opt/tomcat8
chown -R tomcat:tomcat /var/log/tomcat8
chown -R tomcat:tomcat /var/cache/tomcat8
chown tomcat:tomcat /var/cache/tomcat8/tomcat8.pid
chown 664 /var/cache/tomcat8/tomcat8.pid

# 初始化配置文件（首次安装）
if [ ! -d /opt/tomcat8/conf ]; then
    cp -r /opt/tomcat8/conf.dist /opt/tomcat8/conf
    chown -R tomcat:tomcat /opt/tomcat8/conf
fi

# 重载 systemd
systemctl daemon-reload &>/dev/null || :

%files
%defattr(-,tomcat,tomcat,-)
/opt/tomcat8
/var/log/tomcat8
/var/cache/tomcat8
/var/cache/tomcat8/tomcat8.pid
/usr/lib/systemd/system/tomcat8.service

%files native
%{_libexecdir}/tomcat8/jsvc

%changelog
* Mon Aug 24 2026 Your Name <you@example.com> - 8.0.26-2
- 改用默认 NIO + JSSE 连接器，移除 tomcat-native（libtcnative-1）编译与
  useAprConnector 强制，避免 CentOS 8 (OpenSSL 1.1.1) 下的原生库兼容问题；
  原生子包仅保留 commons-daemon jsvc 用于特权端口降权

* Tue Jun 4 2024 Your Name <you@example.com> - 8.0.26-1
- Initial RPM package for Tomcat 8.0.26
- Build commons-daemon (jsvc) natively
