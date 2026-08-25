# tomcat8 — Apache Tomcat 8.0.26 RPM Packaging

将 Apache Tomcat 8.0.26 封装为面向 RHEL / CentOS / Rocky / AlmaLinux（EL8）的 RPM 包，采用默认 NIO + JSSE 连接器（不依赖原生 TLS 库），并附带架构相关的 `tomcat8-native` 子包提供 jsvc 用于特权端口降权。

## 目录

- [特性](#特性)
- [仓库内容](#仓库内容)
- [构建环境](#构建环境)
- [构建 RPM](#构建-rpm)
- [安装与运行](#安装与运行)
- [目录结构](#目录结构)
- [关键配置](#关键配置)
- [常见问题](#常见问题)
- [License](#license)

## 特性

- **双包结构**
  - `tomcat8`（纯 Java 运行时，标记为 `noarch`）：安装到 `/opt/tomcat8`，使用默认 NIO + JSSE 连接器。
  - `tomcat8-native`（架构相关，弱依赖自动安装）：仅编译 `jsvc`（commons-daemon），用于以特权端口（80/443）启动后降权为 `tomcat` 用户。
- **不依赖原生 TLS 库**：本包不编译 `tomcat-native`（libtcnative-1 / APR），因此不受 CentOS 8（OpenSSL 1.1.1）下原生库与 Tomcat 8.0.26 兼容性问题的困扰。
- **配置文件保护**：原始配置存放于 `conf.dist`，首次安装时复制到 `conf`，升级不会被覆盖。
- **Systemd 集成**：提供 `tomcat8.service`，以 `tomcat` 系统用户运行，采用 `catalina.sh run` + `Type=simple`，日志直接进入 journald，`Restart=on-failure`。
- **启动环境兜底**：`setenv.sh` 提供 JVM 启动环境变量钩子，兼容 `x86_64` 与 `aarch64`。

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| `tomcat8.spec` | RPM 构建规范（主包 + native 子包） |
| `setenv.sh` | Tomcat 启动环境补充（JVM 启动变量钩子） |
| `apache-tomcat-8.0.26.tar.gz` | 上游二进制发行包（放入 `~/rpmbuild/SOURCES/`） |
| `tomcat-native-1.3.8-src.tar.gz` | 备用：新版原生库源码；本包当前不编译（与 8.0.26 的 APR 不兼容），仅供需要时自行接入 |

## 构建环境

```bash
# 安装必要工具与编译依赖
sudo dnf install -y rpm-build rpmdevtools gcc make java-1.8.0-openjdk-devel

# 初始化 RPM 目录结构
rpmdev-setuptree
```

> **CentOS 8 兼容性提示**
> - CentOS 8 已 EOL，默认仓库已下线。建议改用 Rocky Linux / AlmaLinux 8，或先将仓库指向 vault：
>   ```bash
>   sudo dnf config-manager --setopt='*.module_hotfixes=1' --save \
>     && sudo sed -i 's|mirrorlist=|#mirrorlist=|; s|#baseurl=http://mirror|baseurl=http://vault|' \
>        /etc/yum.repos.d/CentOS-*.repo
>   sudo dnf makecache
>   ```
> - `rpmdevtools` 位于 PowerTools（CentOS）/ CRB（Rocky/Alma）仓库。若该仓库未启用：
>   ```bash
>   sudo dnf config-manager --set-enabled powertools   # CentOS 8
>   # 或 sudo dnf config-manager --set-enabled crb     # Rocky / Alma 8
>   ```
> - 构建原生库需要 **JDK devel 包**（`java-1.8.0-openjdk-devel`，提供 `jni.h` 与 `javac`），仅安装 `headless` 会因缺少 JNI 头文件而编译失败。

`rpmdev-setuptree` 会创建 `~/rpmbuild`，包含：`BUILD`、`BUILDROOT`、`RPMS`、`SOURCES`、`SPECS`、`SRPMS`。

## 构建 RPM

```bash
# 1. 准备源码（若尚未存在）
wget https://archive.apache.org/dist/tomcat/tomcat-8/v8.0.26/bin/apache-tomcat-8.0.26.tar.gz \
     -O ~/rpmbuild/SOURCES/apache-tomcat-8.0.26.tar.gz

# 2. 复制 SPEC 与辅助文件到对应目录
cp tomcat8.spec     ~/rpmbuild/SPECS/
cp setenv.sh        ~/rpmbuild/SOURCES/

# 3. 构建
cd ~/rpmbuild/SPECS
rpmbuild -bb tomcat8.spec
```

生成的 RPM 位于：

```
~/rpmbuild/RPMS/noarch/tomcat8-8.0.26-3.el8.noarch.rpm
~/rpmbuild/RPMS/x86_64/tomcat8-native-8.0.26-3.el8.x86_64.rpm   # 仅含 jsvc，可按需安装
```

> 实际路径与文件名后缀（如 `.el8`）取决于构建系统。

## 安装与运行

```bash
# 安装（tomcat8-native 为可选弱依赖，仅在使用 jsvc 降权时需要）
sudo dnf install -y ~/rpmbuild/RPMS/noarch/tomcat8-*.rpm \
                    ~/rpmbuild/RPMS/x86_64/tomcat8-native-*.rpm

# 启动并设置开机自启
sudo systemctl enable --now tomcat8
sudo systemctl status tomcat8

# 验证（默认端口 8080）
curl http://localhost:8080
```

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `/opt/tomcat8` | Tomcat 主目录 |
| `/opt/tomcat8/conf.dist` | 出厂配置备份（升级不覆盖） |
| `/opt/tomcat8/conf` | 运行时配置（首次安装由 `conf.dist` 生成） |
| `/var/log/tomcat8` | 日志目录 |
| `/var/cache/tomcat8` | 临时 / 工作目录（`temp`、`work`、`tomcat8.pid`） |
| `/usr/lib/systemd/system/tomcat8.service` | Systemd 服务单元 |

## 关键配置

1. **用户权限**：自动创建系统用户 / 组 `tomcat`，主目录 `/opt/tomcat8`，禁止登录（`/sbin/nologin`）；相关目录均为 `tomcat:tomcat` 所有。
2. **jsvc（可选）**：`tomcat8-native` 子包将 `jsvc` 装入 `/usr/libexec/tomcat8/`，用于绑定特权端口后降权；默认 NIO 连接器（8080）不依赖它。
3. **启动环境钩子**：`setenv.sh` 仅在未显式指定时追加 JVM 启动变量，避免覆盖既有 `JAVA_OPTS`。
4. **资源限制**：服务单元设置 `LimitNOFILE=65536`、`LimitNPROC=4096`。

## 常见问题

| 问题 | 解决方式 |
| --- | --- |
| 依赖错误 | 确保已安装 `java-1.8.0-openjdk-devel`、`gcc`、`make`（编译 jsvc 需要） |
| 权限问题 | 检查 `/opt/tomcat8`、`/var/log/tomcat8`、`/var/cache/tomcat8` 归属是否为 `tomcat` |
| 端口冲突 | 修改 `/opt/tomcat8/conf/server.xml` 中的连接器端口 |
| HTTPS / TLS 配置 | 本包使用 JSSE（Java 内置 TLS），在 `conf/server.xml` 配置 `<Connector port="8443" protocol="org.apache.coyote.http11.Http11NioProtocol" SSLEnabled="true">` 即可，无需原生库 |

## License

- Tomcat 本身采用 [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)。
- 本仓库的 `tomcat8.spec` 与 `setenv.sh` 同样以 Apache-2.0 授权。
