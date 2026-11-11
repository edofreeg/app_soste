[app]
title = Soste Autisti
package.name = soste
package.domain = org.tuonome
source.dir = .
source.include_exts = py
version = 0.1.0
requirements = python3,kivy==2.3.0,android,pyjnius,androidstorage4kivy
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 29
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
p4a.branch = v2024.01.21
