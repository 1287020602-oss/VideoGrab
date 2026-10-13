# VideoGrab · 视频、封面与 MP3 下载工具

粘贴链接，保存视频、封面和 MP3。一个简洁的 Windows 本地媒体下载工具，支持中英文界面、字号调整和手机扫码访问。

**当前应用版本：2.3.2 · Windows 10 / 11 x64**

[下载最新版本](https://github.com/1287020602-oss/VideoGrab/releases/latest) · [更新记录](CHANGELOG.md) · [反馈问题](https://github.com/1287020602-oss/VideoGrab/issues/new/choose)

## 功能介绍

| 功能 | 说明 |
| --- | --- |
| 视频下载 | 粘贴视频页面链接或部分媒体直链，解析后下载到本机 |
| 画质选择 | 最佳、4K、2K、1080p、720p、480p；实际画质以原视频可用格式为准 |
| 封面保存 | 单独下载封面图，也可与视频一起保存 |
| MP3 提取 | 单独保存音频，或同时下载视频、封面和 MP3 |
| 视频解析 | 查看标题、来源、时长和可用格式 |
| 本机管理 | 自选保存位置、命名方式，并查看下载历史 |
| 浏览器登录状态 | 可选择本机已登录的 Edge / Chrome，供自己有权限访问的内容使用 |
| 网络代理 | 设置已有代理服务的地址，适应自己的网络环境；软件不提供代理服务 |
| 中英文界面 | 中文 / English 切换，选择会保存在本机 |
| 字号调整 | 90%、100%、115%、130% 四档字号；Windows 使用微软雅黑 UI |
| 手机二维码 | 电脑与手机处于同一 Wi-Fi 时，可扫码打开配套网页 |
| 临时公网网页 | 通过客户端生成临时访问链接与二维码，供浏览器访问 |

支持 yt-dlp 可识别的常见平台，包括 YouTube、B站、TikTok、Instagram 等，也支持部分普通网页和媒体直链。**这不表示任意平台、任意链接都能下载**：网站接口、账号权限、地区和网络情况都会影响结果。

手机与公网网页依赖电脑客户端持续运行。公网链接是临时链接，重新开启时可能改变，不是永久托管的在线服务；公开网页模式不读取本机浏览器登录状态，并设有请求限制和临时文件清理。

## 快速使用

1. 打开 VideoGrab，粘贴视频页面链接。
2. 勾选要保存的视频、封面或 MP3，可同时选择多项。
3. 选择画质与保存文件夹。
4. 可先点击“解析”查看信息，再点击“下载所选内容”。
5. 如果内容需要登录，选择自己已登录的浏览器；如果需要代理，在设置中填入正在运行的代理地址。

浏览器 cookies 或代理并不能保证解决所有人机验证与访问限制。遇到问题请先查看具体错误提示，再通过 Issues 反馈。

## 持续更新与修复

**本项目将持续维护和迭代**，重点跟进视频平台接口变化、下载引擎更新、解析与下载故障、Windows 兼容性以及使用体验改进。

- 每次正式产品更新后，同步 GitHub 源码、更新说明、安装包、便携版和源码依赖包。
- 新版本统一发布在 [Releases](https://github.com/1287020602-oss/VideoGrab/releases)，变更记录维护在 [CHANGELOG.md](CHANGELOG.md)。
- 用户可下载安装包覆盖升级；保留固定安装 AppId，设置与历史存放在 `%LOCALAPPDATA%\VideoGrab`，不会随正常覆盖安装被清空。
- 当前没有应用内自动升级或后台自动修复。后续可逐步完善更新检查、签名和发布体验；这些是计划方向，不是已上线功能。
- 不承诺固定更新周期或修复期限，也不保证所有链接始终可用。

### 反馈问题与建议

请使用 [问题反馈 / 功能建议](https://github.com/1287020602-oss/VideoGrab/issues/new/choose)。报告问题时附上软件版本、Windows 版本、复现步骤、错误提示，以及可以公开的示例链接。

**不要上传密码、cookies、配对密钥、带私人令牌的链接、完整浏览器数据或个人下载记录。**提交截图或日志前请先遮挡个人信息。Issues 是公开的。

## 使用边界

请只下载自己拥有版权或已获得授权保存的内容。本工具不提供绕过 DRM、付费限制、验证码或私密权限的能力。第三方组件遵循各自许可证，参见 [第三方说明](outputs/VideoGrab/THIRD_PARTY_NOTICES.txt)。

## 换电脑：直接安装

1. 打开 [Releases 下载页](https://github.com/1287020602-oss/VideoGrab/releases/latest)，公开项目无需登录即可下载。
2. 下载 `VideoGrab-2.3.2-Setup-x64.exe` 双击安装；或下载 `Portable-x64.zip`，全部解压后运行 `VideoGrab/VideoGrab.exe`。
3. 无须安装 Python、Node 或 FFmpeg，运行依赖均已包含。新电脑自行设置下载目录及必要的代理。

安装版和便携版已包含运行依赖。当前没有 macOS、Android 或 iOS 原生安装包；手机使用配套网页。

应用尚未签名，Windows 智能应用控制等安全功能可能拦截。公开发布不会赋予可信数字签名，请不要为安装而关闭系统安全保护。

## 继续开发或重新构建

推荐从本仓库主分支获取最新源码，再从 Releases 的 `VideoGrab-2.3.2-Source-with-dependencies-x64.zip` 恢复 `outputs/VideoGrab/vendor` 到相同位置。

```powershell
git clone https://github.com/1287020602-oss/VideoGrab.git
cd VideoGrab
```

历史源码依赖包包含对应发布时的完整源码、构建配置和精确 vendor 文件，不含虚拟环境和个人数据，可解压到任意路径。**最新介绍和维护脚本以本仓库主分支为准**。

安装官方 Python 3.12 x64（含 Tcl/Tk），然后在源码根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\work\bootstrap.ps1 -Python "C:\Python312\python.exe"
.\work\videograb-venv\Scripts\python.exe .\work\test_videograb.py
```

双击 `outputs/VideoGrab/Start VideoGrab.cmd` 启动源码版。打包安装器还需官方 Inno Setup 6，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\work\build_release.ps1
```

bootstrap 需要访问 Python 包源来安装锁定版本的依赖，并按 `work/vendor-sha256.json` 校验 vendor 文件。

## 维护者：更新与发布

验证改动、统一提高版本号、提交本次源码后，运行以下命令。需要 Git 和已登录的官方 GitHub CLI（`gh auth login`）。

```powershell
powershell -ExecutionPolicy Bypass -File .\work\publish_release.ps1 -Repository "1287020602-oss/VideoGrab"
```

脚本默认要求目标仓库为公开仓库，并检查 origin 一致。它构建产品包、导出完整源码依赖、推送当前提交与新版本标签，上传附件并校验远端大小和 SHA256，全部通过后才发布草稿；不会自动修改仓库可见性或提交无关修改。备份现有已验证安装包可加 `-SkipBuild`。

私有派生仓库可明确传入 `-ExpectedVisibility PRIVATE`。同一产品版本仅更新维护工具时，可使用新的 `-ReleaseTag v2.3.2-public.1`；已有版本标签和正式发布附件不会被自动覆盖。

未来更新时按 AGENTS.md 执行此流程。这不是应用内自动升级或后台定时任务；没有执行发布流程的本地修改不会自动上传。

## 隐私与备份范围

保留桌面中英文、四档字号、手机二维码、临时公网网页与代理功能的源码及构建输入。不包含个人下载、cookies、历史、代理设置、配对密钥或凭据。

下载文件、设置和历史保存在本机。公开手机/网页链接会让持有该链接的人访问临时网页，请只在需要时开启。

网站支持取决于 yt-dlp 当前能力及访问权限，不保证任意视频均可下载。
