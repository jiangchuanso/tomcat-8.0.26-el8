Name:           tomcat8
Version:        8.0.26
Release:        4%{?dist}
Summary:        Apache Tomcat 8 Servlet/JSP Container

License:        Apache-2.0
URL:            https://tomcat.apache.org/
Source0:        apache-tomcat-%{version}.tar.gz
Source1:        setenv.sh

# 纯 Java 运行时，整包 noarch，无需编译依赖
Requires:       java-headless >= 1:1.8.0

# 主包为纯 Java 运行时，标记为 noarch
BuildArch:      noarch

%description
Apache Tomcat is an open source implementation of the Java Servlet and
JavaServer Pages technologies.

%prep
%setup -q -n apache-tomcat-%{version}

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

# 安装自定义 setenv.sh（JVM 启动环境变量兜底，不依赖原生库）
install -m 0644 %{SOURCE1} %{buildroot}/opt/tomcat8/bin/setenv.sh

# 创建 systemd 服务文件（catalina.sh run + Type=simple，日志直接进入 journald）
mkdir -p %{buildroot}/usr/lib/systemd/system
cat > %{buildroot}/usr/lib/systemd/system/tomcat8.service <<EOF
[Unit]
Description=Apache Tomcat 8
After=syslog.target network.target

[Service]
Type=simple
User=tomcat
Group=tomcat

Environment=CATALINA_HOME=/opt/tomcat8
Environment=CATALINA_BASE=/opt/tomcat8
Environment=CATALINA_PID=/var/cache/tomcat8/tomcat8.pid

ExecStart=/opt/tomcat8/bin/catalina.sh run
SuccessExitStatus=143

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

%changelog
* Tue Aug 25 2026 Your Name <you@example.com> - 8.0.26-4
- 移除 tomcat8-native 子包与 jsvc 编译，整包变为纯 Java noarch，
  不再区分处理器架构，工作流只需单次构建（x86_64 / aarch64 产物一致）

* Tue Aug 25 2026 Your Name <you@example.com> - 8.0.26-3
- systemd 服务改用 `catalina.sh run` + `Type=simple`，日志直接进入 journald；
  移除 startup.sh/shutdown.sh 的 forking 方式，并加 SuccessExitStatus=143
  以将 SIGTERM 正常退出码视为成功停止

* Mon Aug 24 2026 Your Name <you@example.com> - 8.0.26-2
- 改用默认 NIO + JSSE 连接器，移除 tomcat-native（libtcnative-1）编译与
  useAprConnector 强制，避免 CentOS 8 (OpenSSL 1.1.1) 下的原生库兼容问题；
  原生子包仅保留 commons-daemon jsvc 用于特权端口降权

* Tue Jun 4 2024 Your Name <you@example.com> - 8.0.26-1
- Initial RPM package for Tomcat 8.0.26
- Build commons-daemon (jsvc) natively
