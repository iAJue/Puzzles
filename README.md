# 拼图切割 & 拼图界面

本项目包含两个工具：

- `jigsaw_split.py`：把一张图片切成“现实拼图”那种凹凸形状的碎片（PNG 透明背景）。
- `puzzle_viewer.html`：本地拼图界面，选择碎片文件夹后拖动拼图到中间容器进行拼合。

## 依赖

- Python 3
- Pillow（PIL）

安装依赖：

```bash
pip install pillow
```

## 生成拼图碎片

基础用法（3 行 4 列，输出到 `pieces`，固定随机种子便于复现）：

```bash
python jigsaw_split.py sample.png --rows 3 --cols 4 --output pieces --seed 7
```

参数说明：

- `sample.png`：输入图片路径
- `--rows`：行数
- `--cols`：列数
- `--output`：输出目录（会生成 `piece_r{row}_c{col}.png`）
- `--seed`：随机种子（控制凹凸分布；相同 seed 每次生成相同布局）

## 打开拼图界面

直接用浏览器打开 `puzzle_viewer.html`：

1. 点击“选择碎片文件夹”
2. 选择上一步生成的 `pieces` 文件夹
3. 拖动碎片到中间容器拼合（靠近正确格子会吸附）

