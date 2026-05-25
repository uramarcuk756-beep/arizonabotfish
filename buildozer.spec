[app]
title = ArizonaFish Bot
package.name = arizonafish
package.domain = org.botfish

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy,pillow,pyjnius

orientation = portrait

osx.python_version = 3
osx.kivy_version = 1.9.1

fullscreen = 0

android.minapi = 26
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.private_storage = True

android.permissions = SYSTEM_ALERT_WINDOW, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE, INTERNET

android.accept_sdk_license = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
