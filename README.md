# JQ CORE 今日课表

适用于 Windows 10/11 x64 的桌面课表工具。登录系统后会在屏幕右下角显示下一节课，
点击提示卡即可进入完整周课表。

## 下载

从 [Releases](../../releases/latest) 下载
`Timetable-1.1.0-Windows-x64-portable.zip`，完整解压后运行 `今日课表.exe`。
便携版已经包含 Python 和运行依赖，不需要单独安装环境。

## 功能

- 根据上海建桥学院官方 2026-2027 学年校历计算当前教学周
- 显示下一节课、上课时间、教室、课程类型和实时倒计时
- 可视化展示当前周的 5 天课程矩阵
- 导入学校课表 PDF 后自动生成新课表并保存
- 使用 Pixiv 作品 `126364462` 作为固定背景
- 支持桌面快捷方式、开始菜单快捷方式和开机启动提示
- 首次启动提供经典安装向导，可随时通过 `--setup` 重新配置

## 源码运行

需要 Python 3.12：

```powershell
python -m pip install --requirement requirements.txt
python app.py
```

显示开机提示：

```powershell
pythonw app.py --startup
```

## Docker

构建并运行测试镜像：

```powershell
docker build --target test -t next-class-app:test .
```

构建最终镜像：

```powershell
docker build --target runtime -t next-class-app:1.1.0 .
```

Linux 容器中的 Tkinter 窗口需要 X11、WSLg 或其他图形转发。

## 导入课表 PDF

打开课表后点击右上角 `导入课表 PDF`，选择学校导出的课表文件。程序会读取课程、
周次、节次、课程类型和地点，生成新课表并保存到用户配置目录，下次启动自动使用。
也可以直接把 PDF 文件拖到 `今日课表.exe` 上自动导入。

当前解析器适用于包含星期表格和文字内容的文本型课表 PDF，暂不支持扫描图片型 PDF。

## 快捷方式与启动提示

首次启动会显示经典安装向导，可创建：

```powershell
python app.py --setup
```

可以按需要选择：

- 桌面 `今日课表`
- 开始菜单 `今日课表`
- 启动文件夹 `今日课表-开机提示`

安装完成后向导会直接打开课表。需要重新配置时运行 `--setup`。

## 数据维护

课表和计算逻辑位于 `schedule_data.py`，PDF 解析位于 `schedule_pdf.py`。
导入的课表只包含周次，因此学期第 1 周周一仍按校历起始日期计算。每学期开学后，
需要将 `DEFAULT_SEMESTER_START` 更新为校历第 1 周周一。

当前数据来源：

- 学校导出的课表 PDF
- 上海建桥学院 2026-2027 学年官方校历

## 素材说明

界面背景使用 Pixiv 作品 `126364462` 的本地处理版本。公开分发或商用前，请确认原作品
的授权范围。
