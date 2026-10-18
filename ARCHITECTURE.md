# 随身日语听力跟读 (jp-reader) 架构与协作规范

## 一、模块职责与物理隔离原则（AI 严禁跨文件乱改）
1. index.html：纯 DOM 骨架，日常永不修改。
2. style.css：视觉样式表（必须保留 .jp-text 与 .cn-text 的换行样式）。
3. lessons-config.js：课程目录配置表（日常新增课程唯一修改的文件）。
4. app.js：核心播放引擎（必须保留 coreAudio 原生标签、preservesPitch 变速不变调、mediaSession 蓝牙控制，且严禁在 .mp3 后加 ?t= 动态时间戳以免破坏音频跳转）。

## 二、日常加新课流程
1. 将 {id}.mp3 和 {id}.json 放入 ./lessons/ 目录。
2. 在 lessons-config.js 数组末尾追加一行，并将 default: true 移至新课。
3. 运行：git add . && git commit -m "feat: add new lesson" && git push

## 三、一键回滚到 v-stable 黄金稳定版
cd /Users/binhe/jp-reader && git checkout v-stable -- . && git commit -m "revert: rollback to v-stable" && git push
