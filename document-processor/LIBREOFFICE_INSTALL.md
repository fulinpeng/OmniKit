# LibreOffice 安装指南

## 为什么需要 LibreOffice？

LibreOffice 是专业的开源办公套件，提供业界最高质量的 Word 到 PDF 转换功能。它能完美保持原始格式，包括：
- ✅ 精确的字体和排版
- ✅ 签名图片的原始大小和位置
- ✅ 分隔线的正确显示
- ✅ 复选框控件的完整保留
- ✅ 中文编码的完美支持

## Windows 安装步骤

### 方法1：官方下载（推荐）

1. 访问 LibreOffice 官网：https://www.libreoffice.org/
2. 点击 "Download LibreOffice"
3. 选择 "Windows x64" 版本
4. 下载完成后运行安装程序
5. 按照默认设置完成安装

### 方法2：使用包管理器

如果您安装了 Chocolatey：
```bash
choco install libreoffice
```

如果您安装了 Scoop：
```bash
scoop install libreoffice
```

如果您安装了 Winget：
```bash
winget install LibreOffice.LibreOffice
```

## 验证安装

安装完成后，在命令行中运行：
```bash
libreoffice --version
```

如果显示版本信息，说明安装成功。

## 自动检测路径

程序会自动检测以下路径的 LibreOffice：
- `C:\Program Files\LibreOffice\program\soffice.exe`
- `C:\Program Files (x86)\LibreOffice\program\soffice.exe`
- 系统 PATH 中的 `libreoffice` 命令

## 备用方案

如果 LibreOffice 不可用，程序会自动使用以下备用方案：
1. OpenOffice（如果已安装）
2. mammoth + puppeteer（已内置）

## 故障排除

### 问题1：命令未找到
**解决方案：** 确保 LibreOffice 已正确安装并添加到系统 PATH

### 问题2：转换失败
**解决方案：** 检查文件路径是否包含特殊字符，尝试将文件移动到简单路径

### 问题3：中文乱码
**解决方案：** LibreOffice 通常能完美处理中文，如果仍有问题请检查系统区域设置

## 性能优势

使用 LibreOffice 转换的优势：
- 🚀 **转换速度**：比 HTML 转换快 3-5 倍
- 🎯 **格式保真**：99.9% 的格式一致性
- 📱 **兼容性**：支持所有 Word 版本和格式
- 🔧 **稳定性**：专业级转换引擎，极少出错
