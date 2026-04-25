[app]

# 应用名称
title = 学习助手

# 包名
package.name = studyapp
package.domain = com.studyapp

# 源代码目录
source.dir = .

# 包含的文件类型
source.include_exts = py,png,jpg,kv,atlas,ttf,csv,db

# 排除的目录
source.exclude_dirs = .venv,tests,files,.git,.claude,__pycache__,.vscode
source.exclude_patterns = build_apk_colab.py,scp_*.py,ssh_cmd.py,gh_proxy.py,Python-*.tgz,SDL2-*.tar.gz,kivy-*.zip

# 版本号
version = 1.0.0

# 依赖
requirements = python3==3.11.5,kivy==2.3.0,plyer,requests,pyjnius

# 横屏 + 全屏 (适配21.5寸学习机)
orientation = landscape
fullscreen = 1

# Android 配置
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.enable_androidx = True
android.add_activity_args = android:hardwareAccelerated="true"
android.theme = @android:style/Theme.DeviceDefault.NoActionBar
android.save_data = False
android.allow_backup = False

# Android 权限
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# 日志过滤
android.logcat_filters = *:S python:D
