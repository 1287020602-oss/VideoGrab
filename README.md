# VideoGrab · 私有产品备份

Windows 10/11 x64 视频、封面和 MP3 下载工具。当前版本 **2.3.2**。

## 换电脑：直接安装

1. 登录自己的 GitHub 账号，打开本仓库 **Releases**。
2. 下载 `VideoGrab-2.3.2-Setup-x64.exe` 双击安装；或下载 `Portable-x64.zip`，全部解压后运行 `VideoGrab/VideoGrab.exe`。
3. 无须安装 Python、Node 或 FFmpeg，运行依赖均已包含。新电脑自行设置下载目录及必要的代理。

应用尚未签名；GitHub 私有备份不会赋予可信数字签名，Windows 智能应用控制仍可能拦截。不要为此关闭系统安全保护。

## 继续开发或重新构建

下载 Releases 中的 `VideoGrab-2.3.2-Source-with-dependencies-x64.zip`，包含源码、构建配置和精确 vendor 文件，不含虚拟环境和个人数据。可解压到任意路径。

安装官方 Python 3.12 x64（含 Tcl/Tk），然后在源码根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\work\bootstrap.ps1 -Python "C:\Python312\python.exe"
.\work\videograb-venv\Scripts\python.exe .\work\test_videograb.py
```

双击 `outputs/VideoGrab/Start VideoGrab.cmd` 启动源码版。打包安装器还需官方 Inno Setup 6，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\work\build_release.ps1
```

若用 git clone 而非完整源码包，先从 Releases 下载完整源码包，将其中 `outputs/VideoGrab/vendor` 复制到同一位置。bootstrap 会按 `work/vendor-sha256.json` 校验依赖。

## 每次更新都备份

验证改动、统一提高版本号、提交本次源码后，运行以下命令。需要 Git 和已登录的官方 GitHub CLI（`gh auth login`）。

```powershell
powershell -ExecutionPolicy Bypass -File .\work\publish_release.ps1 -Repository "1287020602-oss/VideoGrab"
```

脚本验证仓库为私有，构建安装包与便携版，打包完整源码依赖，推送当前提交与版本 tag，并上传全部附件及 SHA256 清单。附件核验完成后才发布 draft。初次备份现有已验证安装包可加 `-SkipBuild`。

同一产品版本仅更新备份工具时，可使用新的 `-ReleaseTag v2.3.2-backup.1`；已有版本标签不会被覆盖。

未来更新时按 AGENTS.md 执行此流程。这不是应用内自动升级或后台定时任务；没有执行发布流程的本地修改不会自动上传。

## 备份范围

保留桌面中英文、四档字号、手机二维码、临时公网网页与代理功能的源码及构建输入。不包含个人下载、cookies、历史、代理设置、配对密钥或凭据。

网站支持取决于 yt-dlp 当前能力及访问权限，不保证任意视频均可下载。
