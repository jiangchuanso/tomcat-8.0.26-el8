# tomcat-el8 — Apache Tomcat RPM Packaging (EL8)

将 Apache Tomcat 封装为面向 RHEL / CentOS / Rocky / AlmaLinux（EL8）的 **纯 Java `noarch`** RPM 包。采用默认 NIO + JSSE 连接器，不编译任何原生库，因此不区分处理器架构，单次构建即可（x86_64 / aarch64 产物一致）。

**按版本自由构建**：`tomcat.spec` 是版本无关模板，版本与主版本号由构建时注入。推送 `vX.Y.Z` 这样的 tag（或手动指定版本），工作流会自动从 Apache 官方归档下载对应的 `apache-tomcat-X.Y.Z.tar.gz` 并打包。

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

- **整包 `noarch`**：纯 Java 运行时，安装到 `/opt/tomcat<主版本号>`（如 8 → `/opt/tomcat8`，9 → `/opt/tomcat9`），使用默认 NIO + JSSE 连接器；不编译任何 C/原生代码，故不区分 x86_64 / aarch64，工作流只需单次构建。
- **按版本自由构建**：版本由 `tomcat_version`、主版本号由 `tomcat_major` 注入（`rpmbuild --define`），默认构建 Tomcat 8.0.26；工作流按 git tag 的 `v` 版本号自动下载对应源码包。
- **不依赖原生 TLS 库**：本包不编译 `tomcat-native`（libtcnative-1 / APR），因此不受 CentOS 8（OpenSSL 1.1.1）下原生库兼容性问题的困扰。
- **配置文件保护**：原始配置存放于 `conf.dist`，首次安装时复制到 `conf`，升级不会被覆盖。
- **Systemd 集成**：提供 `tomcat<主版本号>.service`，以 `tomcat` 系统用户运行，采用 `catalina.sh run` + `Type=simple`，日志直接进入 journald，`Restart=on-failure`。
- **启动环境钩子**：`setenv.sh` 提供 JVM 启动环境变量钩子。

## 仓库内容

| 文件 | 说明 |
| --- | --- |
| `tomcat.spec` | RPM 构建规范（版本无关模板，整包 `noarch`） |
| `setenv.sh` | Tomcat 启动环境补充（JVM 启动变量钩子） |
| `apache-tomcat-*.tar.gz` | 上游二进制发行包（**不在仓库内**，由工作流按 tag 版本自动从官方归档下载） |

> 旧版曾附带的 `tomcat-native-1.3.8-src.tar.gz` 因 tarball 与 Tomcat 8.0.26 的 APR 连接器 JNI 接口不兼容，且本包已改为纯 Java noarch，故不再编译原生库，该文件已移除。

## 构建环境

```bash
# 安装必要工具（纯 Java 包，无需 gcc/make/JDK 编译依赖）
sudo dnf install -y rpm-build rpmdevtools

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
> - 本包为纯 Java `noarch`，**运行只需 JRE**（`java-headless >= 1.8`），构建无需 JDK devel / 原生编译工具链。

`rpmdev-setuptree` 会创建 `~/rpmbuild`，包含：`BUILD`、`BUILDROOT`、`RPMS`、`SOURCES`、`SPECS`、`SRPMS`。

## 构建 RPM

### 方式一：GitHub Actions（推荐，按 tag 自动下载）

推送一个版本 tag 即可触发构建与发布：

```bash
git tag v8.0.26
git push origin v8.0.26
```

工作流会：

1. 从 tag 取出版本号（`v8.0.26` → `8.0.26`，主版本号 `8`）；
2. 下载 `https://archive.apache.org/dist/tomcat/tomcat-8/v8.0.26/bin/apache-tomcat-8.0.26.tar.gz` 并用 GPG 签名（`.asc`）校验完整性（注：并非每个版本都发布 sha1/sha512 摘要，但每个版本都提供 `.asc`）；
3. 以 `rpmbuild --define "tomcat_version 8.0.26" --define "tomcat_major 8"` 构建；
4. 在 tag 推送时自动创建 GitHub Release 并上传 RPM。

也支持手动触发（`workflow_dispatch`），在输入框填写任意版本（如 `9.0.80`），工作流同样按该版本下载并构建。

### 方式二：本地手动构建

```bash
# 1. 下载对应版本的上游发行包
VER=8.0.26
MAJOR=${VER%%.*}
wget "https://archive.apache.org/dist/tomcat/tomcat-${MAJOR}/v${VER}/bin/apache-tomcat-${VER}.tar.gz" \
     -O ~/rpmbuild/SOURCES/apache-tomcat-${VER}.tar.gz

# 2. 复制 SPEC 与辅助文件到对应目录
cp tomcat.spec  ~/rpmbuild/SPECS/
cp setenv.sh    ~/rpmbuild/SOURCES/

# 3. 构建（注入版本 / 主版本号）
cd ~/rpmbuild/SPECS
rpmbuild -bb --define "tomcat_version ${VER}" --define "tomcat_major ${MAJOR}" tomcat.spec
```

生成的 RPM 位于：

```
~/rpmbuild/RPMS/noarch/tomcat8-8.0.26-1.el8.noarch.rpm
```

> 整包为 `noarch`，x86_64 与 aarch64 构建产物一致，工作流只需单次构建。包名与主版本号随版本变化（如 9.0.80 → `tomcat9-9.0.80-1.el8.noarch.rpm`）。实际文件名后缀（如 `.el8`）取决于构建系统。

## 安装与运行

```bash
# 安装（默认主版本 8 时）
sudo dnf install -y ~/rpmbuild/RPMS/noarch/tomcat8-*.rpm

# 启动并设置开机自启（服务名随主版本号：8 → tomcat8，9 → tomcat9）
sudo systemctl enable --now tomcat8
sudo systemctl status tomcat8

# 验证（默认端口 8080）
curl http://localhost:8080
```

## 目录结构

以默认主版本号 8 为例：

| 路径 | 说明 |
| --- | --- |
| `/opt/tomcat8` | Tomcat 主目录 |
| `/opt/tomcat8/conf.dist` | 出厂配置备份（升级不覆盖） |
| `/opt/tomcat8/conf` | 运行时配置（首次安装由 `conf.dist` 生成） |
| `/opt/tomcat8/logs`、`temp`、`work` | 符号链接，分别指向 `/var/log/tomcat8`、`/var/cache/tomcat8/temp`、`/var/cache/tomcat8/work` |
| `/var/log/tomcat8` | 日志目录 |
| `/var/cache/tomcat8` | 临时 / 工作目录（`temp`、`work`、`tomcat8.pid`） |
| `/usr/lib/systemd/system/tomcat8.service` | Systemd 服务单元 |

> 主版本号非 8 时，上述路径中的 `8` 相应替换为 `9` / `10` 等（如 `tomcat9`、`/opt/tomcat9`）。

## 关键配置

1. **用户权限**：自动创建系统用户 / 组 `tomcat`，主目录 `/opt/tomcat<主版本号>`，禁止登录（`/sbin/nologin`）；相关目录均为 `tomcat:tomcat` 所有。
2. **启动环境钩子**：`setenv.sh` 仅在未显式指定时追加 JVM 启动变量，避免覆盖既有 `JAVA_OPTS`。
3. **资源限制**：服务单元设置 `LimitNOFILE=65536`、`LimitNPROC=4096`。

## 常见问题

| 问题 | 解决方式 |
| --- | --- |
| 依赖错误 | 运行需 `java-headless >= 1.8`；构建只需 `rpm-build` / `rpmdevtools`，无需 gcc/make/JDK |
| 权限问题 | 检查 `/opt/tomcat<主版本号>`、`/var/log/tomcat<主版本号>`、`/var/cache/tomcat<主版本号>` 归属是否为 `tomcat` |
| 端口冲突 | 修改 `/opt/tomcat<主版本号>/conf/server.xml` 中的连接器端口 |
| HTTPS / TLS 配置 | 本包使用 JSSE（Java 内置 TLS），在 `conf/server.xml` 配置 `<Connector port="8443" protocol="org.apache.coyote.http11.Http11NioProtocol" SSLEnabled="true">` 即可，无需原生库 |
| 想构建其他版本 | 推送对应 `vX.Y.Z` tag，或手动 `workflow_dispatch` 填写版本；工作流自动下载并构建 |

## License

- Tomcat 本身采用 [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)。
- 本仓库的 `tomcat.spec` 与 `setenv.sh` 同样以 Apache-2.0 授权。
