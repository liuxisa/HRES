#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动将 Cloudflare R2 加载逻辑添加到 Godot 导出的 index.html 文件

使用方法:
    python add_r2_to_index.py

默认配置:
    - 文件路径: game/index.html
    - R2_BASE_URL: https://cdn.hres.world
"""

import re
import sys
import json
import os

# 默认配置
DEFAULT_HTML_PATH = "game/index.html"
DEFAULT_R2_BASE_URL = "https://cdn.hres.world"


def extract_file_sizes(godot_config_str):
    """从 GODOT_CONFIG 字符串中提取文件大小"""
    # 尝试解析 JSON
    try:
        config_match = re.search(r'const GODOT_CONFIG = ({.*?});', godot_config_str, re.DOTALL)
        if config_match:
            config_json = config_match.group(1)
            config = json.loads(config_json)
            file_sizes = config.get('fileSizes', {})
            pck_size = file_sizes.get('index.pck', 0)
            wasm_size = file_sizes.get('index.wasm', 0)
            return pck_size, wasm_size
    except Exception as e:
        print(f"警告: 无法解析 GODOT_CONFIG: {e}")
    
    # 如果解析失败，尝试使用正则表达式提取
    pck_match = re.search(r'"index\.pck":(\d+)', godot_config_str)
    wasm_match = re.search(r'"index\.wasm":(\d+)', godot_config_str)
    pck_size = int(pck_match.group(1)) if pck_match else 0
    wasm_size = int(wasm_match.group(1)) if wasm_match else 0
    return pck_size, wasm_size


def generate_r2_code(r2_base_url, pck_size, wasm_size):
    """生成 R2 加载代码"""
    r2_config = f'''// R2 存储配置 - 从 Cloudflare R2 加载大文件
const R2_BASE_URL = '{r2_base_url}';

'''
    
    r2_loading_logic = f'''		setStatusMode('progress');
		
		// 从 R2 加载大文件
		const pckUrl = `${{R2_BASE_URL}}/index.pck`;
		const wasmUrl = `${{R2_BASE_URL}}/index.wasm`;
		console.log('从 R2 加载大文件...');
		console.log('PCK:', pckUrl);
		console.log('WASM:', wasmUrl);
		
		// 先预加载 PCK 文件到虚拟文件系统
		engine.preloadFile(pckUrl, 'index.pck', {pck_size}).then(() => {{
			console.log('PCK 文件预加载完成，加载 WASM 引擎...');
			// 从 R2 加载 WASM 文件（使用 basePath，会自动添加 .wasm 后缀）
			const wasmBasePath = `${{R2_BASE_URL}}/index`;
			return engine.load(wasmBasePath, {wasm_size});
		}}).then(() => {{
			console.log('引擎加载完成，初始化...');
			// 初始化引擎（不需要参数，因为 engine.load 已经设置了 loadPromise）
			return engine.init();
		}}).then(() => {{
			console.log('引擎初始化完成，启动游戏...');
			// 设置启动参数（PCK 文件已经在虚拟文件系统中）
			engine.config.args = ['--main-pack', 'index.pck'].concat(engine.config.args);
			// 启动游戏
			return engine.start({{
				'onProgress': function (current, total) {{
					if (current > 0 && total > 0) {{
						statusProgress.value = current;
						statusProgress.max = total;
					}} else {{
						statusProgress.removeAttribute('value');
						statusProgress.removeAttribute('max');
					}}
				}},
			}});
		}}).then(() => {{
			setStatusMode('hidden');
		}}, (err) => {{
			console.error('从 R2 加载失败:', err);
			displayFailureNotice('从 R2 加载失败: ' + (err.message || err));
		}});'''
    
    return r2_config, r2_loading_logic


def add_r2_to_index(html_path, r2_base_url):
    """将 R2 加载逻辑添加到 index.html"""
    # 读取文件
    if not os.path.exists(html_path):
        print(f"错误: 文件不存在: {html_path}")
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取文件大小
    pck_size, wasm_size = extract_file_sizes(content)
    if pck_size == 0 or wasm_size == 0:
        print(f"警告: 无法从 GODOT_CONFIG 中提取文件大小 (PCK: {pck_size}, WASM: {wasm_size})")
        print("将使用默认值，如果文件大小不正确，请手动修改脚本中的值")
        if pck_size == 0:
            pck_size = 114529632  # 默认值，应该从实际文件中获取
        if wasm_size == 0:
            wasm_size = 43699190  # 默认值，应该从实际文件中获取
    
    print(f"检测到文件大小: index.pck = {pck_size}, index.wasm = {wasm_size}")
    
    # 生成 R2 代码
    r2_config, r2_loading_logic = generate_r2_code(r2_base_url, pck_size, wasm_size)
    
    # 检查是否已经包含 R2 配置和加载逻辑
    has_r2_config = 'const R2_BASE_URL' in content
    has_r2_loading = '从 R2 加载大文件' in content and 'engine.preloadFile(pckUrl' in content
    
    if has_r2_config and has_r2_loading:
        print("检测到文件已包含 R2 配置和加载逻辑，将更新配置和文件大小")
        # 更新 R2 配置
        r2_base_url_pattern = r"const R2_BASE_URL = '.*?';"
        content = re.sub(r2_base_url_pattern, f"const R2_BASE_URL = '{r2_base_url}';", content)
        # 移除旧的 USE_R2 配置（如果存在）
        content = re.sub(r'const USE_R2 = .*?;\s*\n', '', content)
        # 更新文件大小
        pck_size_pattern = r"engine\.preloadFile\(pckUrl, 'index\.pck', \d+\)"
        wasm_size_pattern = r"engine\.load\(wasmBasePath, \d+\)"
        content = re.sub(pck_size_pattern, f"engine.preloadFile(pckUrl, 'index.pck', {pck_size})", content)
        content = re.sub(wasm_size_pattern, f"engine.load(wasmBasePath, {wasm_size})", content)
        print("已更新 R2 配置和文件大小")
    elif has_r2_config:
        print("警告: 检测到部分 R2 配置（缺少加载逻辑），将清理并重新添加完整逻辑")
        # 移除旧的 R2 配置（包括 USE_R2）
        content = re.sub(r'// R2 存储配置.*?const R2_BASE_URL = .*?;\s*\n', '', content, flags=re.DOTALL)
        content = re.sub(r'const USE_R2 = .*?;\s*\n', '', content)
        # 插入新的 R2 配置
        config_match = re.search(r'(const GODOT_CONFIG = .*?;)\s*\n(const GODOT_THREADS_ENABLED)', content, re.DOTALL)
        if config_match:
            content = content[:config_match.end(1)] + '\n' + r2_config + content[config_match.start(2):]
            print("已插入 R2 配置")
    else:
        # 插入新的 R2 配置
        config_match = re.search(r'(const GODOT_CONFIG = .*?;)\s*\n(const GODOT_THREADS_ENABLED)', content, re.DOTALL)
        if config_match:
            # 在 GODOT_CONFIG 和 GODOT_THREADS_ENABLED 之间插入 R2 配置
            content = content[:config_match.end(1)] + '\n' + r2_config + content[config_match.start(2):]
            print("已在 GODOT_CONFIG 后插入 R2 配置")
        else:
            print("警告: 无法找到 GODOT_CONFIG，将在 engine 初始化后插入")
            engine_match = re.search(r'(const engine = new Engine\(GODOT_CONFIG\);)\s*\n', content)
            if engine_match:
                content = content[:engine_match.end()] + '\n' + r2_config + content[engine_match.end():]
                print("已在 engine 初始化后插入 R2 配置")
            else:
                print("错误: 无法找到插入点")
                return False
    
    # 如果已经有完整的 R2 加载逻辑，就不需要替换了
    if not has_r2_loading:
        # 查找并替换 engine.startGame 调用
        # 查找 setStatusMode('progress') 到对应的 } 结束之间的内容
        # 先尝试匹配 else 块中的情况
        progress_pattern = r"(\s+} else \{\s*\n\s+)setStatusMode\(['\"]progress['\"]\);\s*\n\s+engine\.startGame\(.*?setStatusMode\(['\"]hidden['\"]\);.*?\}, displayFailureNotice\);\s*\n\s+}"
        
        match = re.search(progress_pattern, content, re.DOTALL)
        if match:
            # 找到了 else 块中的 engine.startGame
            indent = match.group(1)
            # 保留 else 块的开头，替换后面的内容
            replacement = indent + r2_loading_logic + '\n\t}'
            content = re.sub(progress_pattern, replacement, content, flags=re.DOTALL)
            print("已替换 else 块中的 engine.startGame 调用为 R2 加载逻辑")
        else:
            # 尝试匹配不带 else 的情况（在某些 Godot 版本中可能没有 else）
            simple_pattern = r"(\s+)setStatusMode\(['\"]progress['\"]\);\s*\n\s+engine\.startGame\(.*?setStatusMode\(['\"]hidden['\"]\);.*?\}, displayFailureNotice\);"
            match = re.search(simple_pattern, content, re.DOTALL)
            if match:
                indent = match.group(1)
                replacement = indent + r2_loading_logic
                content = re.sub(simple_pattern, replacement, content, flags=re.DOTALL)
                print("已替换 engine.startGame 调用为 R2 加载逻辑")
            else:
                print("错误: 无法找到 engine.startGame 调用")
                print("调试信息: 搜索以下模式:")
                print("  - setStatusMode('progress')")
                print("  - engine.startGame")
                # 尝试找到相关的代码行
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'startGame' in line or 'setStatusMode' in line:
                        print(f"  行 {i+1}: {line.strip()}")
                return False
    
    # 写回文件
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 成功将 R2 加载逻辑添加到 {html_path}")
    print(f"  R2_BASE_URL: {r2_base_url}")
    return True


def main():
    """主函数：一键执行，使用默认配置"""
    
    print("正在添加 R2 加载逻辑到 index.html...")
    print(f"文件路径: {DEFAULT_HTML_PATH}")
    print(f"R2_BASE_URL: {DEFAULT_R2_BASE_URL}")
    print()
    
    if not os.path.exists(DEFAULT_HTML_PATH):
        print(f"错误: 文件不存在: {DEFAULT_HTML_PATH}")
        print(f"请确保 Godot 已经导出项目到 {DEFAULT_HTML_PATH}")
        return 1
    
    success = add_r2_to_index(DEFAULT_HTML_PATH, DEFAULT_R2_BASE_URL)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
