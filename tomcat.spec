# 版本无关模板：tomcat_version / tomcat_major 由构建时 --define 注入，
# 默认构建 Tomcat 8.0.26。工作流按 git tag 的 v 版本号传入对应值即可自由构建。
# 版本由构建时 --define 注入；命令行已传入时此处默认值不生效（spec 内 define 会覆盖命令行，故用守卫）
%{!?tomcat_version: %define tomcat_version 8.0.26}
%{!?tomcat_major: %define tomcat_major 8}

Name:           tomcat%{tomcat_major}
Version:        %{tomcat_version}
Release:        3%{?dist}
Summary:        Apache Tomcat %{tomcat_major} Servlet/JSP Container

License:        Apache-2.0
URL:            https://tomcat.apache.org/
Source0:        apache-tomcat-%{version}.tar.gz
Source1:        setenv.sh

# 纯 Java 运行时，整包 noarch，无需编译依赖
Requires:       java-headless >= 1:1.8.0

# 主包为纯 Java 运行时，标记为 noarch
BuildArch:      noarch

# 安装路径随主版本号变化（tomcat8 -> /opt/tomcat8，tomcat9 -> /opt/tomcat9 ...）
%define tomcat_home  /opt/tomcat%{tomcat_major}
%define tomcat_log   /var/log/tomcat%{tomcat_major}
%define tomcat_cache /var/cache/tomcat%{tomcat_major}

%description
Apache Tomcat is an open source implementation of the Java Servlet and
JavaServer Pages technologies.

%prep
%setup -q -n apache-tomcat-%{version}

%install
rm -rf %{buildroot}

# 安装 Tomcat 到 %{tomcat_home}
mkdir -p %{buildroot}%{tomcat_home}
cp -R * %{buildroot}%{tomcat_home}

# 移除仅用于编译的源码包与解压目录（不进入最终包）
rm -f  %{buildroot}%{tomcat_home}/bin/commons-daemon-native.tar.gz
rm -f  %{buildroot}%{tomcat_home}/bin/tomcat-native.tar.gz
rm -rf %{buildroot}%{tomcat_home}/commons-daemon-*
rm -rf %{buildroot}%{tomcat_home}/tomcat-native-*

# 运行时目录
mkdir -p %{buildroot}%{tomcat_log}
mkdir -p %{buildroot}%{tomcat_cache}/{temp,work}
mv %{buildroot}%{tomcat_home}/conf %{buildroot}%{tomcat_home}/conf.dist
touch %{buildroot}%{tomcat_cache}/tomcat%{tomcat_major}.pid

# Tomcat 默认写 $CATALINA_BASE/{logs,temp,work}（即 /opt/tomcatN）。
# tarball 中的这三个目录是空的，RPM 打包不保留空目录，而 tomcat 用户
# 无权在 /opt 下创建，会导致启动时日志 / JSP work / 临时目录写入失败。
# 故用符号链接指向 /var 下的运行时目录（FHS，与 RHEL tomcat 惯例一致）。
rm -rf %{buildroot}%{tomcat_home}/logs %{buildroot}%{tomcat_home}/temp %{buildroot}%{tomcat_home}/work
ln -s %{tomcat_log}        %{buildroot}%{tomcat_home}/logs
ln -s %{tomcat_cache}/temp %{buildroot}%{tomcat_home}/temp
ln -s %{tomcat_cache}/work %{buildroot}%{tomcat_home}/work

# 安装自定义 setenv.sh（JVM 启动环境变量兜底，不依赖原生库）
install -m 0644 %{SOURCE1} %{buildroot}%{tomcat_home}/bin/setenv.sh

# 创建 systemd 服务文件（catalina.sh run + Type=simple，日志直接进入 journald）
mkdir -p %{buildroot}/usr/lib/systemd/system
cat > %{buildroot}/usr/lib/systemd/system/tomcat%{tomcat_major}.service <<EOF
[Unit]
Description=Apache Tomcat %{tomcat_major}
After=syslog.target network.target

[Service]
Type=simple
User=tomcat
Group=tomcat

Environment=CATALINA_HOME=%{tomcat_home}
Environment=CATALINA_BASE=%{tomcat_home}
Environment=CATALINA_PID=%{tomcat_cache}/tomcat%{tomcat_major}.pid

ExecStart=%{tomcat_home}/bin/catalina.sh run
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
    useradd -r -s /sbin/nologin -d %{tomcat_home} -g tomcat tomcat
fi

# 设置目录权限
chown -R tomcat:tomcat %{tomcat_home}
chown -R tomcat:tomcat %{tomcat_log}
chown -R tomcat:tomcat %{tomcat_cache}
chown tomcat:tomcat %{tomcat_cache}/tomcat%{tomcat_major}.pid
chmod 664 %{tomcat_cache}/tomcat%{tomcat_major}.pid

# 初始化配置文件（首次安装）
if [ ! -d %{tomcat_home}/conf ]; then
    cp -r %{tomcat_home}/conf.dist %{tomcat_home}/conf
    chown -R tomcat:tomcat %{tomcat_home}/conf
fi

# 重载 systemd
systemctl daemon-reload &>/dev/null || :

%files
%defattr(-,tomcat,tomcat,-)
%{tomcat_home}
%{tomcat_log}
%{tomcat_cache}
/usr/lib/systemd/system/tomcat%{tomcat_major}.service

%changelog
* Tue Sep 01 2026 Your Name <you@example.com> - 8.0.26-3
- 修复 %files 中 pid 文件重复声明导致 rpmbuild 报 "File listed twice" 构建失败
* Tue Aug 25 2026 Your Name <you@example.com> - 2026.08.25-2
- 修复 %post 中 `chown 664` 笔误为 `chmod 664`（原会报 invalid user 导致脚本失败）
- 修复运行时目录缺失：/opt/tomcatN/{logs,temp,work} 改为指向 /var/log 与
  /var/cache 的符号链接，避免 tomcat 用户无权限创建导致日志 / JSP 编译失败
* Tue Aug 25 2026 Your Name <you@example.com> - 2026.08.25
- 重构为版本无关模板：Version/Major 由 rpmbuild --define 注入，
  支持按 git tag 版本下载对应 apache-tomcat-*.tar.gz 自由构建 noarch RPM
- 纯 Java noarch 包，默认 NIO + JSSE 连接器，无需原生编译
