[app]

# (str) Title of your application
title = Image Search

# (str) Version of your application
version = 0.1

# (str) Package name
package.name = imagesearch

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html,css,js,txt

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,flask,requests,android,jnius,openssl,sqlite3,werkzeug==2.3.7

# (str) Custom source folders to include in the package
# source.include_patterns = assets/*,images/*.png

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (string) Presplash background color (for new android toolchain)
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
#android.presplash_color = #FFFFFF

# (string) Presplash animation using Lottie format.
# see https://lottiefiles.com/ for examples and https://airbnb.io/lottie/
# see also https://github.com/kivy/kivy/blob/master/kivy/core/window/_window_sdl2.py#L36-L53
#android.presplash_lottie = "path/to/lottie/file.json"

# (str) Adaptive icon of the application (used if Android API level is 26+ at least)
#icon.adaptive_foreground.filename = %(source.dir)s/data/icon_fg.png
#icon.adaptive_background.filename = %(source.dir)s/data/icon_bg.png

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible (usually 33+)
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
#android.ndk = 19b

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
#android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (list) Pattern to exclude from the source.dir
#android.skip_update = False

# (bool) Process the application as an OpenGL ES 2 application
#android.numeric_version = 1

# (str) The format used to package the app for release mode (aab or apk or aar).
#android.release_artifact = aab

# (str) The format used to package the app for debug mode (apk or aar).
#android.debug_artifact = apk

# (list) List of Java classes to add to the compilation
#android.add_jars = foo.jar,bar.jar,common/one.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files)
#android.add_src =

# (list) Android AAR archives to add
#android.add_aars =

# (list) Put these files or directories in the apk assets directory.
#android.add_assets =

# (list) Gradle dependencies to add
#android.gradle_dependencies =

# (bool) Enable AndroidX support. Enable when 'android.gradle_dependencies'
# contains an 'androidx' package, or any package from Kotlin source.
# android.enable_androidx requires pygame 2.1.2+
#android.enable_androidx = False

# (list) Add java compile options
# this can for example be necessary when importing certain java libraries using the 'android.gradle_dependencies' option
# see https://developer.android.com/studio/write/java8-support for more information
#android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"

# (list) Gradle repositories to add {can be necessary for some android.gradle_dependencies}
# please enclose in double quotes 
#android.gradle_repositories = "maven { url 'https://jitpack.io' }"

# (list) Packaging options
# see https://google.github.io/android-gradle-dsl/current/com.android.build.gradle.internal.dsl.PackagingOptions.html
# can be necessary to solve conflicts when using the 'android.gradle_dependencies' option
#android.add_packaging_options = "exclude 'META-INF/common.kotlin_module'", "exclude 'META-INF/*.kotlin_module'"

# (list) Java classes to add to the android manifest
#android.add_activities = com.example.ExampleActivity

# (str) OUYA Console category. Should be one of GAME or APP
#android.ouya.category = GAME

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters = intent_filters.xml

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (bool) Indicate whether the screen should stay on
# Don't sleep on touch
#android.wakelock = False

# (str) Android meta-data to add (key=value format)
#android.meta_data =

# (str) Android library references to add (key=value format)
#android.library_references =

# (bool) Android logcat, control the log output to logcat
#android.logcat_filters = *:S python:D

# (str) Android additional adb arguments
#android.adb_args = -H host -P port

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (int) overrides automatic versionCode computation (used in build.gradle)
# this is not the same as app version and should only be edited if you know what you're doing
# android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
# (bool) enables Android auto backup feature (Android API >=23)
# android.allow_backup = True

# (str) XML file for custom backup rules (see official auto backup documentation)
# android.backup_rules = 

# (str) If you need to insert variables into your AndroidManifest.xml file,
# you can do so with the manifestPlaceholders property.
# This property takes a map of key-value pairs. (one per line)
# android.manifest_placeholders = {
#     'myCustomPlaceholder': 'myCustomValue'
# }

# (bool) disables the compilation of py to pyc/pyo files
# android.no-compile-pyo = True
# (str) The format used to package the app for release mode (aab or apk or aar).
# android.release_artifact = aab

# (str) The format used to package the app for debug mode (apk or aar).
# android.debug_artifact = apk

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters = intent_filters.xml

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (str) Screen orientation
orientation = portrait

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (bool) Indicate whether the screen should stay on
# Don't sleep on touch
#android.wakelock = False

# (str) Android meta-data to add (key=value format)
#android.meta_data =

# (str) Android library references to add (key=value format)
#android.library_references =

# (bool) Android logcat, control the log output to logcat
#android.logcat_filters = *:S python:D

# (str) Android additional adb arguments
#android.adb_args = -H host -P port

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
#android.archs = arm64-v8a

# (int) overrides automatic versionCode computation (used in build.gradle)
# this is not the same as app version and should only be edited if you know what you're doing
# android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True
android.manifest.application_attributes = android:usesCleartextTraffic="true"

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (list) List of service to declare
# services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

# (str) The main.py file name
# main.py = main.py

# (list) List of Java classes to add to the compilation
# android.add_jars = foo.jar,bar.jar,common/one.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files)
# android.add_src =

# (list) Android AAR archives to add
# android.add_aars =

# (list) Gradle dependencies to add
# android.gradle_dependencies =

# (bool) Use the local p4a (python-for-android) instead of downloading it
# p4a.source_dir =

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
