# Click 经典阅读

独立安装的离线阅读器，最低 Android 4.0（API 14）。支持 32 位 ARMv7、64 位 ARM、x86 和 x86-64。BlackBerry Passport 的 BlackBerry 10.3 兼容运行时对应 Android 4.3（API 18）。安装 APK 后，从书库选择本机 PDF 或 EPUB。Android 4.x 的「打开文件」也可直接浏览存储目录。

PDF 默认按阅读区高度显示原页，菜单可切换适合宽度。要选字、查词、标红、备注或朗读，选择「可选文字」。扫描页需要已有文字层。EPUB 可直接长按选段或轻点英文单词。上下文菜单支持标红和备注，查词卡可反复播放。朗读使用设备安装的语音引擎及语言包。底部按钮与实体左右方向键可翻页。书籍、阅读位置、标红和备注保存在本机；此版本没有桌面书库同步和 OCR。

同一文件重复打开会回到上次阅读位置。经典版的包名为 `com.click.classic`，与现有的 `com.click.shell` 独立。

## 构建

在 macOS 安装 JDK 17、Xcode 命令行工具、Android SDK Platform 35 和 Build Tools 35.0.0，设置 `JAVA_HOME` 和 `ANDROID_HOME`。在本目录运行以下命令，将参数替换为本机路径。

```sh
python3 build.py --cache /path/to/build-cache --out /path/to/Click-Classic.apk \
  --keystore /path/to/release.p12 --alias click-release --password-file /path/to/keystore-password
```

构建脚本核对下载依赖的 SHA-256，用支持 API 14 的 PdfiumAndroid 显示 PDF，复用主安卓工程的 EPUB 解析器。英汉词典使用 ECDICT 的常用和分级词条。签名完成后验证 Android 4 所需的 v1 签名。第三方许可随 APK 打包。
