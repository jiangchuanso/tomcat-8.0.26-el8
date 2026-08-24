要将 Tomcat 8.0.26 打包成 RPM，请按照以下详细步骤操作：

---

### **1. 准备构建环境**

```bash
# 安装必要工具
sudo yum install -y rpm-build rpmdevtools gcc make

# 初始化 RPM 目录结构
rpmdev-setuptree
```

此时会创建 `~/rpmbuild` 目录，包含以下子目录：  

- `BUILD`, `BUILDROOT`, `RPMS`, `SOURCES`, `SPECS`, `SRPMS`

---

### **2. 准备 Tomcat 源码**

```bash
# 下载 Tomcat 8.0.26
wget https://archive.apache.org/dist/tomcat/tomcat-8/v8.0.26/bin/apache-tomcat-8.0.26.tar.gz \
     -O ~/rpmbuild/SOURCES/apache-tomcat-8.0.26.tar.gz
```

---

### **3. 创建 SPEC 文件**

在 `~/rpmbuild/SPECS/tomcat8.spec` 创建如下内容：

```spec
Name:           tomcat8
Version:        8.0.26
Release:        1%{?dist}
Summary:        Apache Tomcat 8 Servlet/JSP Container

License:        Apache-2.0
URL:            https://tomcat.apache.org/
Source0:        apache-tomcat-%{version}.tar.gz

BuildArch:      noarch
Requires:       java-headless >= 1:1.8.0

%description
Apache Tomcat is an open source implementation of the Java Servlet and JavaServer Pages technologies.

%prep
%setup -q -n apache-tomcat-%{version}

%install
# 清空安装目录
rm -rf %{buildroot}

# 安装 Tomcat 到 /opt/tomcat8
mkdir -p %{buildroot}/opt/tomcat8
cp -R * %{buildroot}/opt/tomcat8

# 创建运行时目录
mkdir -p %{buildroot}/var/log/tomcat8
mkdir -p %{buildroot}/var/cache/tomcat8/{temp,work}

# 创建配置文件备份
mv %{buildroot}/opt/tomcat8/conf %{buildroot}/opt/tomcat8/conf.dist

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
Environment=CATALINA_PID=/var/run/tomcat8.pid

ExecStart=/opt/tomcat8/bin/startup.sh
ExecStop=/opt/tomcat8/bin/shutdown.sh

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
/usr/lib/systemd/system/tomcat8.service

%changelog
* Tue Jun 4 2024 Your Name <you@example.com> - 8.0.26-1
- Initial RPM package for Tomcat 8.0.26
```

---

### **4. 构建 RPM 包**

```bash
cd ~/rpmbuild/SPECS
rpmbuild -bb tomcat8.spec
```

生成的 RPM 位于：  
`~/rpmbuild/RPMS/noarch/tomcat8-8.0.26-1.el7.noarch.rpm`（路径可能因系统而异）

---

### **5. 安装与测试**

```bash
# 安装 RPM
sudo yum install -y ~/rpmbuild/RPMS/noarch/tomcat8-*.rpm

# 启动服务
sudo systemctl start tomcat8
sudo systemctl status tomcat8

# 验证（默认端口 8080）
curl http://localhost:8080
```

---

### **关键配置说明**

1. **目录结构**  
   
   - `/opt/tomcat8`：Tomcat 主目录  
   - `/var/log/tomcat8`：日志目录  
   - `/var/cache/tomcat8`：临时文件目录  

2. **用户权限**  
   自动创建系统用户 `tomcat`，所有文件归属此用户。

3. **配置文件保护**  
   首次安装时从 `conf.dist` 复制配置到 `conf`，避免升级覆盖。

4. **Systemd 集成**  
   服务文件：`/usr/lib/systemd/system/tomcat8.service`

---

### **常见问题解决**

- **依赖错误**：确保已安装 Java（`yum install java-1.8.0-openjdk-headless`）。  
- **权限问题**：检查 `/opt/tomcat8` 和日志目录的所有权是否为 `tomcat` 用户。  
- **端口冲突**：修改 `/opt/tomcat8/conf/server.xml` 中的端口号。

通过此流程，您已成功将 Tomcat 8.0.26 封装为可部署的 RPM 包。