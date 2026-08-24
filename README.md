# tomcat8 — Apache Tomcat 8.0.26 RPM Packaging

将 Apache Tomcat 8.0.26 封装为面向 RHEL / CentOS / Rocky / AlmaLinux（EL8）的 RPM 包，包含纯 Java 运行时主包与架构相关的原生库子包（APR 连接器 + jsvc 降权）。

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
  - `tomcat8`（纯 Java 运行时，标记为 `noarch`）：安装到 `/opt/tomcat8`。
  - `tomcat8-native`（架构相关）：编译 `libtcnative-1`（基于 APR 的 TLS / 网络加速）与 `jsvc`（commons-daemon 降权启动），作为主包的弱依赖自动安装。
- **APR 连接器**：自动在 `server.xml` 中开启 `useAprConnector="true"`，获得更好的 TLS 与网络性能。
- **配置文件保护**：原始配置存放于 `conf.dist`，首次安装时复制到 `conf`，升级不会被覆盖。
- **Systemd 集成**：提供 `tomcat8.service`，以 `tomcat` 系统用户运行，`Restart=on-failure`。
- **跨架构兜底**：`setenv.sh` 自动组装 `java.library.path`，兼容 `x86_64` 与 `aarch64`。

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| `tomcat8.spec` | RPM 构建规范（主包 + native 子包） |
| `setenv.sh` | Tomcat 启动环境补充，确保 JVM 找到 `libtcnative-1.so` |
| `apache-tomcat-8.0.26.tar.gz` | 上游二进制发行包（放入 `~/rpmbuild/SOURCES/`） |

## 构建环境

```bash
# 安装必要工具与编译依赖
sudo dnf install -y rpm-build rpmdevtools gcc make autoconf libtool \
     openssl-devel apr-devel java-1.8.0-openjdk-headless

# 初始化 RPM 目录结构
rpmdev-setuptree
```

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
~/rpmbuild/RPMS/noarch/tomcat8-8.0.26-1.el8.noarch.rpm
~/rpmbuild/RPMS/x86_64/tomcat8-native-8.0.26-1.el8.x86_64.rpm   # 架构相关
```

> 实际路径与文件名后缀（如 `.el8`）取决于构建系统。

## 安装与运行

```bash
# 安装（主包会自动 Recommends 安装 native 子包）
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
2. **原生库**：`libtcnative-1.so` 装入 `/usr/lib64`（位于 JRE 默认 `java.library.path`），`jsvc` 装入 `/usr/libexec/tomcat8/`。
3. **java.library.path 兜底**：`setenv.sh` 仅在未显式指定时追加，避免覆盖既有 `JAVA_OPTS`。
4. **资源限制**：服务单元设置 `LimitNOFILE=65536`、`LimitNPROC=4096`。

## 常见问题

| 问题 | 解决方式 |
| --- | --- |
| 依赖错误 | 确保已安装 `java-1.8.0-openjdk-headless` 及编译依赖 |
| 权限问题 | 检查 `/opt/tomcat8`、`/var/log/tomcat8`、`/var/cache/tomcat8` 归属是否为 `tomcat` |
| 端口冲突 | 修改 `/opt/tomcat8/conf/server.xml` 中的连接器端口 |
| APR 未生效 | 确认 `tomcat8-native` 已安装且 `setenv.sh` 已就位，检查 `catalina.out` 中 APR 监听日志 |

## License

- Tomcat 本身采用 [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)。
- 本仓库的 `tomcat8.spec` 与 `setenv.sh` 同样以 Apache-2.0 授权。
