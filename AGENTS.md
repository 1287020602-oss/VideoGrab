# VideoGrab 公开发布与维护

本目录是 VideoGrab 正式源码与构建目录：应用在 outputs/VideoGrab，构建配置在 work。

用户在 2026-10-13 明确要求公开项目，允许任何人下载，并清楚说明功能和持续更新修复。此要求取代之前的“仅私有备份”限制。今后每次产品更新，验证后同步源码和对应安装包、便携版、源码依赖包及 SHA256 校验文件；不得把本地修改或上传尝试称为已发布。

- 正式仓库为 origin 对应的 1287020602-oss/VideoGrab，当前应为 PUBLIC，以用户后续明确指定为准。公开前复查完整 Git 历史和发布附件，避免泄露个人数据。发布脚本只验证可见性，不自行更改可见性。
- 发布时统一提高 app.py、mobile/server.py、VideoGrab.iss、version_info.txt 和说明里的版本号，保留安装 AppId。
- 运行 work/test_videograb.py、桌面 smoke test 和适合改动的验证；联网下载测试与离线测试分别如实报告。
- 构建使用 work/build_release.ps1；源码依赖包使用 work/package_backup.ps1；发布使用 work/publish_release.ps1。
- 先提交本次相关修改，再发布；不能盲目提交用户无关改动，发布脚本不自动提交。
- vendor、大型安装包存入 Releases，不放 Git 历史。未经用户授权，不替项目擅自添加宽泛的源码许可证。
- 不上传本机设置/历史、浏览器 cookies、手机配对 token、代理配置、下载媒体、凭据、虚拟环境和构建缓存。
- 用户数据始终保留在 %LOCALAPPDATA%/VideoGrab。迁移机器不复制原设备代理及登录状态。
- 被网络/授权/权限阻断时保留本地产物，明确告知尚未上传和需要的操作。
- 功能介绍必须区分已支持能力与后续计划；持续维护不代表保证所有链接可用、保证修复期限或应用内自动升级。修复与正式发布同步更新 README 和 CHANGELOG。
- 公开 Issues 不收集 cookies、密码、配对密钥或私人视频。历史发布标签与完整源码依赖快照保留，不为文档更新重写旧标签或覆盖旧产品包；开发以主分支为准。
