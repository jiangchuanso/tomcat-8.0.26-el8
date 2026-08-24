Name:           tomcat8
Version:        8.0.26
Release:        1%{?dist}
Summary:        Apache Tomcat 8 Servlet/JSP Container

License:        Apache-2.0
URL:            https://tomcat.apache.org/
Source0:        apache-tomcat-%{version}.tar.gz

# Native 编译依赖（libtcnative-1 / jsvc 需要 C 工具链与 apr/openssl）
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  autoconf
BuildRequires:  libtool
BuildRequires:  openssl-devel
BuildRequires:  apr-devel
BuildRequires:  java-1.8.0-openjdk-headless
Requires:       java-headless >= 1:1.8.0

%description
Apache Tomcat is an open source implementation of the Java Servlet and
JavaServer Pages technologies.

# 主包：纯 Java 运行时，标记为 noarch
%package -n tomcat8
BuildArch:      noarch
Summary:        Apache Tomcat 8 Servlet/JSP Container (Java runtime)
%description -n tomcat8
Apache Tomcat 8 (pure-Java runtime) installed to /opt/tomcat8.

# 原生子包：按架构分别编译（x86_64 / aarch64）
%package native
Summary:        Tomcat 8 native libraries (tomcat-native / commons-daemon jsvc)
%description native
Architecture-specific native components for Tomcat 8:
- libtcnative-1  (基于 APR 的 TLS / 网络加速库)
- jsvc           (commons-daemon，用于以特权端口启动后降权)

%prep
%setup -q -n apache-tomcat-%{version}

%build
# 探测 JAVA_HOME（容器内为 java-1.8.0-openjdk-headless）
export JAVA_HOME=$(ls -d /usr/lib/jvm/java-1.8.0-openjdk 2>/dev/null | head -1)
if [ -z "$JAVA_HOME" ]; then
    JAVA_HOME=$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")
fi
export JAVA_HOME

# 编译 commons-daemon (jsvc)
tar xzf bin/commons-daemon-native.tar.gz
pushd commons-daemon-*/src/native/unix
./configure --with-java="$JAVA_HOME"
make
popd

# 编译 tomcat-native (libtcnative-1)
tar xzf bin/tomcat-native.tar.gz
pushd tomcat-native-*/native
./configure --with-apr --with-ssl --with-java-home="$JAVA_HOME" --prefix=%{_prefix}
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

# 安装 native 库
# libtcnative-1 直接装入 %{_libdir} (/usr/lib64)，位于 JRE 默认 java.library.path
install -m 0755 tomcat-native-*/native/.libs/libtcnative-1.so* %{buildroot}%{_libdir}/
# jsvc 装入 libexec，避免污染 PATH
mkdir -p %{buildroot}%{_libexecdir}/tomcat8
install -m 0755 commons-daemon-*/src/native/unix/jsvc %{buildroot}%{_libexecdir}/tomcat8/jsvc

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

%post -n tomcat8
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

%post native
ldconfig || :

%postun native
ldconfig || :

%files -n tomcat8
%defattr(-,tomcat,tomcat,-)
/opt/tomcat8
/var/log/tomcat8
/var/cache/tomcat8
/var/cache/tomcat8/tomcat8.pid
/usr/lib/systemd/system/tomcat8.service

%files native
%{_libdir}/libtcnative-1.so*
%{_libexecdir}/tomcat8/jsvc

%changelog
* Tue Jun 4 2024 Your Name <you@example.com> - 8.0.26-1
- Initial RPM package for Tomcat 8.0.26
- Build tomcat-native (libtcnative-1) and commons-daemon (jsvc) natively
