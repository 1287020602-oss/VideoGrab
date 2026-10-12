# VideoGrab 私有备份与维护

本目录是 VideoGrab 正式源码与构建目录：应用在 outputs/VideoGrab，构建配置在 work。

用户要求：今后每次产品更新，验证后都要把源码提交推送到用户的私有 GitHub 仓库，并上传对应安装包、便携版、完整源码依赖包和 SHA256 校验文件。不得把本地修改或上传尝试称为已备份。

- 上传目标为 origin 对应的用户私有仓库（首次为 1287020602-oss/VideoGrab），以用户后续明确指定为准。发布前验证 PRIVATE，禁止公开。
- 发布时统一提高 app.py、mobile/server.py、VideoGrab.iss、version_info.txt 和说明里的版本号，保留安装 AppId。
- 运行 work/test_videograb.py、桌面 smoke test 和适合改动的验证；联网下载测试与离线测试分别如实报告。
- 构建使用 work/build_release.ps1；源码依赖包使用 work/package_backup.ps1；发布使用 work/publish_release.ps1。
- 先提交本次相关修改，再发布；不能盲目提交用户无关改动，发布脚本不自动提交。
- vendor、大型安装包仅存入私有 Releases，不放 Git 历史。
- 不上传本机设置/历史、浏览器 cookies、手机配对 token、代理配置、下载媒体、凭据、虚拟环境和构建缓存。
- 用户数据始终保留在 %LOCALAPPDATA%/VideoGrab。迁移机器不复制原设备代理及登录状态。
- 被网络/授权/权限阻断时保留本地产物，明确告知尚未上传和需要的操作。
