#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动配置 game/index.html 以使用 IndexedDB 加载游戏文件

使用方法:
    python setup_game_index.py

默认配置:
    - 文件路径: game/index.html
    - 将修改 else 块中的加载逻辑，改为从 IndexedDB 加载
"""

import re
import sys
import json
import os

# 默认配置
DEFAULT_HTML_PATH = "game/index.html"


def extract_file_sizes(godot_config_str):
    """从 GODOT_CONFIG 字符串中提取文件大小"""
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


def find_and_replace_loading_logic(content):
    """找到并替换加载逻辑"""
    # 查找 setStatusMode('progress') 的位置
    setstatus_pos = content.find("setStatusMode('progress')")
    if setstatus_pos == -1:
        setstatus_pos = content.find('setStatusMode("progress")')
    
    if setstatus_pos == -1:
        return None
    
    # 找到 setStatusMode 行的开始，提取缩进
    line_start = content[:setstatus_pos].rfind('\n') + 1
    indent = content[line_start:setstatus_pos]
    
    # 查找 else 块
    before_setstatus = content[:setstatus_pos]
    else_pos = before_setstatus.rfind('} else {')
    
    if else_pos == -1:
        print("警告: 无法找到 '} else {' 块，将尝试直接替换 setStatusMode 后的内容")
        # 如果没有 else，查找下一个 } 作为结束
        after_setstatus = content[setstatus_pos:]
        brace_count = 0
        block_end = -1
        
        for i, char in enumerate(after_setstatus):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    block_end = setstatus_pos + i + 1
                    break
                brace_count -= 1
        
        if block_end > 0:
            # 查找结束 } 的缩进
            closing_line_start = content[:block_end].rfind('\n') + 1
            closing_indent = content[closing_line_start:block_end].replace('}', '').strip()
            
            replacement_code = '''setStatusMode('progress');
		
		// 使用 IndexedDB 加载游戏文件（逻辑在 game-loader.js 中）
		const fileSizes = GODOT_CONFIG.fileSizes;
		loadGameFromIndexedDB(
			engine,
			statusText,
			statusProgress,
			setStatusText,
			updateProgress,
			setStatusMode,
			displayFailureNotice,
			fileSizes
		).catch((err) => {
			console.error('加载失败:', err);
			displayFailureNotice('加载失败: ' + (err.message || err) + '\\n\\n请先访问加载页面下载游戏文件。');
		});'''
            
            # 调整缩进
            replacement_lines = replacement_code.split('\n')
            adjusted_lines = []
            for line in replacement_lines:
                if line.strip():
                    adjusted_lines.append(indent + line.lstrip())
                else:
                    adjusted_lines.append('')
            
            replacement = '\n'.join(adjusted_lines)
            if not closing_indent:
                closing_indent = indent.rstrip('\t').rstrip(' ')
            
            return content[:setstatus_pos] + replacement + '\n' + closing_indent + '}' + content[block_end:]
        return None
    
    # 找到 else { 行的结束位置
    else_line_end = content.find('\n', else_pos) + 1
    if else_line_end == 0:
        else_line_end = else_pos + len('} else {')
    
    # 查找 else 块的结束 }
    after_setstatus = content[setstatus_pos:]
    brace_count = 1  # 从 else { 的 { 开始
    else_block_end = -1
    
    for i, char in enumerate(after_setstatus):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                else_block_end = setstatus_pos + i + 1
                break
    
    if else_block_end == -1:
        return None
    
    # 构建替换代码
    replacement_code = '''setStatusMode('progress');
		
		// 使用 IndexedDB 加载游戏文件（逻辑在 game-loader.js 中）
		const fileSizes = GODOT_CONFIG.fileSizes;
		loadGameFromIndexedDB(
			engine,
			statusText,
			statusProgress,
			setStatusText,
			updateProgress,
			setStatusMode,
			displayFailureNotice,
			fileSizes
		).catch((err) => {
			console.error('加载失败:', err);
			displayFailureNotice('加载失败: ' + (err.message || err) + '\\n\\n请先访问加载页面下载游戏文件。');
		});'''
    
    # 调整缩进以匹配原始代码
    replacement_lines = replacement_code.split('\n')
    adjusted_lines = []
    for line in replacement_lines:
        if line.strip():
            adjusted_lines.append(indent + line.lstrip())
        else:
            adjusted_lines.append('')
    
    replacement = '\n'.join(adjusted_lines)
    
    # 查找结束 } 的缩进
    closing_line_start = content[:else_block_end].rfind('\n') + 1
    closing_indent = content[closing_line_start:else_block_end].replace('}', '').strip()
    if not closing_indent:
        # 从 else { 行提取缩进
        else_line_start = content[:else_pos].rfind('\n') + 1
        closing_indent = content[else_line_start:else_pos]
    
    # 组合新内容：保留 else { 行，替换 else 块内容
    return content[:else_line_end] + replacement + '\n' + closing_indent + '}' + content[else_block_end:]


def update_loading_html_file_sizes(loading_html_path, pck_size, wasm_size):
    """更新 loading.html 中的文件大小配置（用于进度显示和缓存验证）"""
    if not os.path.exists(loading_html_path):
        print(f"警告: loading.html 不存在: {loading_html_path}，跳过更新")
        return False
    
    with open(loading_html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并替换 FILES 数组中的文件大小
    # 注意：这些大小用于进度显示估算和缓存验证（与缓存文件大小进行比较）
    # 匹配模式: { name: 'index.pck', size: 数字 } 或 { name: "index.pck", size: 数字 }
    pck_pattern = r"(\{\s*name:\s*['\"]index\.pck['\"],\s*size:\s*)\d+(\s*\})"
    wasm_pattern = r"(\{\s*name:\s*['\"]index\.wasm['\"],\s*size:\s*)\d+(\s*\})"
    
    new_content = content
    updated = False
    
    # 替换 index.pck 的大小
    if re.search(pck_pattern, content):
        new_content = re.sub(pck_pattern, f"\\g<1>{pck_size}\\g<2>", new_content)
        updated = True
        print(f"  - 已更新 loading.html 中的 index.pck 大小（用于进度显示和缓存验证）: {pck_size}")
    else:
        print(f"  警告: 无法在 loading.html 中找到 index.pck 的大小配置")
    
    # 替换 index.wasm 的大小
    if re.search(wasm_pattern, content):
        new_content = re.sub(wasm_pattern, f"\\g<1>{wasm_size}\\g<2>", new_content)
        updated = True
        print(f"  - 已更新 loading.html 中的 index.wasm 大小（用于进度显示和缓存验证）: {wasm_size}")
    else:
        print(f"  警告: 无法在 loading.html 中找到 index.wasm 的大小配置")
    
    if updated:
        with open(loading_html_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False


def update_game_index_styles(content):
    """更新 game/index.html 的样式，使其与 loading.html 一致"""
    # 定义新的样式（与 loading.html 一致的样式）
    new_status_styles = '''#status {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	bottom: 0;
	background: linear-gradient(180deg, #1a1a1a 0%, #0f0f0f 100%);
	display: flex;
	flex-direction: column;
	justify-content: center;
	align-items: center;
	visibility: hidden;
	font-family: 'Noto Sans', 'Droid Sans', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

#status-splash {
	display: none;
}

#status-text {
	font-size: 18px;
	font-weight: 500;
	margin-bottom: 50px;
	color: #ffffff;
	text-shadow: 0 2px 4px rgba(0, 0, 0, 0.9);
	letter-spacing: 0.5px;
	line-height: 1.6;
	text-align: center;
	max-width: 700px;
	padding: 0 20px;
	display: none;
}

#status-progress {
	width: 100%;
	max-width: 600px;
	height: 32px;
	border-radius: 16px;
	background-color: rgba(0, 0, 0, 0.6);
	border: 2px solid rgba(255, 255, 255, 0.2);
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
	overflow: hidden;
	margin: 0 auto;
	display: none;
}

#status-progress::-webkit-progress-bar {
	background-color: rgba(0, 0, 0, 0.6);
	border-radius: 16px;
}

#status-progress::-webkit-progress-value {
	background: linear-gradient(90deg, #4a90e2 0%, #357abd 50%, #4a90e2 100%);
	border-radius: 16px;
	transition: width 0.3s ease;
	box-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
}

#status-progress::-moz-progress-bar {
	background: linear-gradient(90deg, #4a90e2 0%, #357abd 50%, #4a90e2 100%);
	border-radius: 16px;
	box-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
}

#status-notice {
	display: none;
	background-color: #5b3943;
	border-radius: 0.5rem;
	border: 1px solid #9b3943;
	color: #e0e0e0;
	font-family: 'Noto Sans', 'Droid Sans', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
	line-height: 1.3;
	margin: 0 2rem;
	overflow: hidden;
	padding: 1rem;
	text-align: center;
	z-index: 1;
}

@media (max-width: 768px) {
	#status-text {
		font-size: 16px;
		margin-bottom: 40px;
		padding: 0 15px;
	}
	
	#status-progress {
		height: 28px;
	}
}'''
    
    # 使用更简单可靠的方法：按行查找并替换
    lines = content.split('\n')
    status_start_line = -1
    status_end_line = -1
    
    # 查找 #status 开始的行
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#status') and '{' in line and status_start_line == -1:
            status_start_line = i
            break
    
    if status_start_line == -1:
        return content, False
    
    # 查找样式块结束的位置（下一个主要选择器，不是 status 相关的）
    for i in range(status_start_line + 1, len(lines)):
        stripped = lines[i].strip()
        # 检查是否是下一个主要样式选择器（但不是 status 相关的）
        if stripped and not stripped.startswith('#status') and not stripped.startswith('@media') and not stripped.startswith('}'):
            if (stripped.startswith('#canvas') or stripped.startswith('html') or stripped.startswith('body')):
                status_end_line = i
                break
        elif stripped.startswith('@media'):
            # 查找 @media 块的结束
            brace_count = 0
            for j in range(i, len(lines)):
                brace_count += lines[j].count('{') - lines[j].count('}')
                if brace_count == 0 and j > i:
                    status_end_line = j + 1
                    break
            if status_end_line > i:
                break
    
    # 如果没找到结束位置，查找 </style>
    if status_end_line == -1:
        for i in range(status_start_line, len(lines)):
            if '</style>' in lines[i]:
                status_end_line = i
                break
    
    if status_end_line == -1:
        return content, False
    
    # 替换样式块
    new_lines = lines[:status_start_line] + new_status_styles.split('\n') + lines[status_end_line:]
    new_content = '\n'.join(new_lines)
    
    # 同时移除 status-splash 图片元素（如果存在）
    # 查找并移除包含 id="status-splash" 或 id='status-splash' 的 img 标签（可能跨多行）
    status_div_start = new_content.find('<div id="status">')
    if status_div_start != -1:
        status_div_end = new_content.find('</div>', status_div_start)
        if status_div_end != -1:
            status_div_content = new_content[status_div_start:status_div_end]
            # 移除 img 标签（支持跨行）
            status_div_content_new = re.sub(r'<img[^>]*id=["\']status-splash["\'][^>]*>', '', status_div_content, flags=re.DOTALL)
            if status_div_content_new != status_div_content:
                new_content = new_content[:status_div_start] + status_div_content_new + new_content[status_div_end:]
                print("    - 已移除 logo 图片（status-splash）")
    
    return new_content, True


def setup_game_index(html_path):
    """配置 game/index.html 以使用 IndexedDB 加载"""
    if not os.path.exists(html_path):
        print(f"错误: 文件不存在: {html_path}")
        return False
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取文件大小
    pck_size, wasm_size = extract_file_sizes(content)
    if pck_size == 0 or wasm_size == 0:
        print(f"警告: 无法从 GODOT_CONFIG 中提取文件大小 (PCK: {pck_size}, WASM: {wasm_size})")
        print("将使用默认值")
        if pck_size == 0:
            pck_size = 114529648
        if wasm_size == 0:
            wasm_size = 43699190
    
    print(f"检测到文件大小: index.pck = {pck_size}, index.wasm = {wasm_size}")
    
    # 更新 loading.html 中的文件大小
    loading_html_path = os.path.join(os.path.dirname(html_path), 'loading.html')
    update_loading_html_file_sizes(loading_html_path, pck_size, wasm_size)
    
    # 更新样式，使其与 loading.html 一致（无论是否已配置，都需要更新样式）
    content, styles_updated = update_game_index_styles(content)
    if styles_updated:
        print("  - 已更新样式，使其与 loading.html 一致（渐变背景、文字和进度条样式）")
    
    # 检查是否已经配置过
    if 'game-loader.js' in content and 'loadGameFromIndexedDB' in content:
        print("检测到文件已配置，无需再次配置")
        # 即使已配置，如果样式更新了，也需要写回文件
        if styles_updated:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("  - 已保存样式更新")
        return True
    
    # 0. 添加必要的 HTML 元素和函数（如果缺失）
    # 检查并添加 status-text 元素
    if 'id="status-text"' not in content and "id='status-text'" not in content:
        status_div_pos = content.find('<div id="status">')
        if status_div_pos != -1:
            # 在 status div 中添加 status-text 元素（在 progress 之前）
            progress_pos = content.find('<progress id="status-progress">', status_div_pos)
            if progress_pos != -1:
                content = content[:progress_pos] + '\t\t\t<div id="status-text"></div>\n' + content[progress_pos:]
                print("已添加 status-text 元素")
    
    # 检查并添加必要的 JavaScript 函数
    if 'function setStatusText' not in content:
        # 在 setStatusMode 函数之后添加
        set_status_mode_end = content.find('function setStatusMode')
        if set_status_mode_end != -1:
            # 找到 setStatusMode 函数的结束位置
            brace_count = 0
            func_start = False
            func_end_pos = -1
            for i in range(set_status_mode_end, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    func_start = True
                elif content[i] == '}':
                    brace_count -= 1
                    if func_start and brace_count == 0:
                        func_end_pos = i + 1
                        break
            
            if func_end_pos > 0:
                # 提取缩进
                line_start = content[:set_status_mode_end].rfind('\n') + 1
                indent = content[line_start:set_status_mode_end]
                
                # 添加函数
                functions_to_add = '''
	function setStatusText(text) {
		if (statusText) {
			statusText.textContent = text;
		}
	}

	function updateProgress(current, total, text) {
		if (current > 0 && total > 0) {
			statusProgress.value = current;
			statusProgress.max = total;
		} else {
			statusProgress.removeAttribute('value');
			statusProgress.removeAttribute('max');
		}
		if (text) {
			setStatusText(text);
		}
	}
'''
                # 调整缩进
                func_lines = functions_to_add.split('\n')
                adjusted_lines = []
                for line in func_lines:
                    if line.strip():
                        adjusted_lines.append(indent + '\t' + line.lstrip())
                    else:
                        adjusted_lines.append('')
                
                content = content[:func_end_pos] + '\n'.join(adjusted_lines) + '\n' + content[func_end_pos:]
                print("已添加 setStatusText 和 updateProgress 函数")
    
    # 检查并添加 statusText 变量声明
    if 'const statusText = document.getElementById' not in content and 'let statusText = document.getElementById' not in content:
        status_progress_pos = content.find('const statusProgress = document.getElementById')
        if status_progress_pos != -1:
            # 在 statusProgress 之后添加 statusText
            line_end = content.find(';', status_progress_pos) + 1
            content = content[:line_end] + '\n\tconst statusText = document.getElementById(\'status-text\');' + content[line_end:]
            print("已添加 statusText 变量声明")
    
    # 更新 setStatusMode 函数以包含 statusText 的显示/隐藏
    if 'statusText.style.display' not in content and 'function setStatusMode' in content:
        status_progress_display = content.find("statusProgress.style.display = mode === 'progress'")
        if status_progress_display != -1:
            # 在 statusProgress.style.display 之后添加 statusText.style.display
            line_end = content.find(';', status_progress_display) + 1
            new_line = '\n\t\tif (statusText) {\n\t\t\tstatusText.style.display = mode === \'progress\' ? \'block\' : \'none\';\n\t\t}'
            content = content[:line_end] + new_line + content[line_end:]
            print("已更新 setStatusMode 函数以包含 statusText")
    
    # 1. 在 index.js 之后添加 game-loader.js 脚本（如果还没有）
    if 'game-loader.js' not in content:
        # 首先查找完整的闭合标签 <script src="index.js"></script>
        index_js_pos = content.find('<script src="index.js"></script>')
        if index_js_pos == -1:
            index_js_pos = content.find("<script src='index.js'></script>")
        
        if index_js_pos != -1:
            # 找到了完整的闭合标签，在它之后添加 game-loader.js
            insert_pos = index_js_pos + len('<script src="index.js"></script>')
            script_tag = '\n\t\t<script src="game-loader.js"></script>'
            content = content[:insert_pos] + script_tag + content[insert_pos:]
            print("已添加 game-loader.js 脚本引用（在 index.js 之后）")
        else:
            # 查找未闭合的开始标签 <script src="index.js">
            index_js_pos = content.find('<script src="index.js">')
            if index_js_pos == -1:
                index_js_pos = content.find("<script src='index.js'>")
            
            if index_js_pos != -1:
                # 找到了开始标签
                script_tag_end = content.find('>', index_js_pos) + 1
                # 检查后面是否有 </script> 闭合标签（在同一行或下一行）
                next_script_close = content.find('</script>', script_tag_end)
                # 检查是否在合理范围内（比如在接下来的200个字符内）
                if next_script_close != -1 and next_script_close < script_tag_end + 200:
                    # 已经有闭合标签，在它之后添加
                    insert_pos = next_script_close + 9  # 9 是 '</script>' 的长度
                    script_tag = '\n\t\t<script src="game-loader.js"></script>'
                else:
                    # 没有闭合标签，先添加闭合标签，然后添加 game-loader.js
                    insert_pos = script_tag_end
                    script_tag = '</script>\n\t\t<script src="game-loader.js"></script>'
                content = content[:insert_pos] + script_tag + content[insert_pos:]
                print("已添加 game-loader.js 脚本引用（在 index.js 之后，已修复未闭合的标签）")
            else:
                # 如果找不到 index.js，尝试在 </body> 之前添加
                body_end = content.rfind('</body>')
                if body_end != -1:
                    script_tag = '\n\t\t<script src="game-loader.js"></script>\n'
                    content = content[:body_end] + script_tag + content[body_end:]
                    print("已添加 game-loader.js 脚本引用（在 </body> 之前）")
                else:
                    print("警告: 无法找到 index.js 或 </body> 标签")
                    return False
    
    # 2. 查找并替换加载逻辑
    new_content = find_and_replace_loading_logic(content)
    if new_content is None:
        print("错误: 无法找到需要替换的加载逻辑")
        print("请确保这是 Godot 导出的标准 index.html 文件")
        print("调试信息: 搜索相关代码...")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'setStatusMode' in line and 'progress' in line:
                print(f"  行 {i+1}: {line.strip()}")
            if 'engine.startGame' in line or 'engine.load' in line:
                print(f"  行 {i+1}: {line.strip()}")
        return False
    
    content = new_content
    
    # 3. 写回文件
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 成功配置 {html_path}")
    print(f"  - 已添加 game-loader.js 引用")
    print(f"  - 已替换加载逻辑为 IndexedDB 加载")
    print(f"  - 文件大小: PCK={pck_size}, WASM={wasm_size}")
    return True


def main():
    """主函数"""
    print("正在配置 game/index.html 以使用 IndexedDB 加载...")
    print(f"文件路径: {DEFAULT_HTML_PATH}")
    print()
    
    if not os.path.exists(DEFAULT_HTML_PATH):
        print(f"错误: 文件不存在: {DEFAULT_HTML_PATH}")
        print(f"请确保 Godot 已经导出项目到 {DEFAULT_HTML_PATH}")
        return 1
    
    success = setup_game_index(DEFAULT_HTML_PATH)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
