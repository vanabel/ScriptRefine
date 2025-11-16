#!/usr/bin/env python3
"""语稿智能整理系统 - Web 应用"""

import os
import json
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import shutil

from script_refine import ScriptRefiner

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 配置
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'txt', 'md', 'text'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 初始化系统
refiner = None

def init_refiner(config_path=None):
    """初始化文本整理系统"""
    global refiner
    try:
        refiner = ScriptRefiner(config_path=config_path)
        return True
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        return False

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_text():
    """处理文本 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        text = data.get('text', '').strip()
        mode = data.get('mode', 'full')  # full, summary, both
        
        if not text:
            return jsonify({'error': '文本内容为空'}), 400
        
        if mode not in ['full', 'summary', 'both']:
            return jsonify({'error': '无效的处理模式'}), 400
        
        if not refiner:
            return jsonify({'error': '系统未初始化'}), 500
        
        # 处理文本
        results = refiner.process_text(
            text=text,
            output_mode=mode,
            show_progress=False
        )
        
        # 准备响应
        response = {
            'success': True,
            'results': {}
        }
        
        if 'full' in results:
            response['results']['full'] = results['full']
        
        if 'summary' in results:
            response['results']['summary'] = results['summary']
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件 API"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式，仅支持 .txt, .md'}), 400
        
        mode = request.form.get('mode', 'full')
        
        if not refiner:
            return jsonify({'error': '系统未初始化'}), 500
        
        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # 处理文件
            results = refiner.process(
                input_path=temp_path,
                output_mode=mode,
                show_progress=False
            )
            
            # 准备响应
            response = {
                'success': True,
                'results': {},
                'downloads': {}
            }
            
            # 读取处理结果
            if 'full' in mode or 'both' in mode:
                # 查找完整版文件
                for format_type, filepath in results.items():
                    if 'summary' not in format_type:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        response['results']['full'] = content
                        response['downloads'][format_type] = filepath
            
            if 'summary' in mode or 'both' in mode:
                # 查找会议纪要文件
                for format_type, filepath in results.items():
                    if 'summary' in format_type:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        response['results']['summary'] = content
                        response['downloads'][format_type] = filepath
            
            return jsonify(response)
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/download')
def download_file():
    """下载文件 API"""
    try:
        filepath = request.args.get('path')
        if not filepath:
            return jsonify({'error': '缺少文件路径参数'}), 400
        
        # 解码路径
        filepath = filepath.replace('\\', '/')
        
        # 安全检查：确保文件在输出目录内
        if not refiner:
            return jsonify({'error': '系统未初始化'}), 500
        
        output_dir = refiner.config.get('output', {}).get('output_dir', './output')
        abs_output_dir = os.path.abspath(output_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_output_dir):
            return jsonify({'error': '无效的文件路径'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )
    
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/api/export', methods=['POST'])
def export_file():
    """导出文件 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        content = data.get('content', '').strip()
        format_type = data.get('format', 'docx')  # docx, pdf, markdown
        mode = data.get('mode', 'full')
        
        if not content:
            return jsonify({'error': '内容为空'}), 400
        
        if format_type not in ['docx', 'pdf', 'markdown']:
            return jsonify({'error': '不支持的格式'}), 400
        
        if not refiner:
            return jsonify({'error': '系统未初始化'}), 500
        
        # 使用导出器导出
        filename_template = f"完整版_{{timestamp}}"
        if mode == 'summary':
            filename_template = f"会议纪要_{{timestamp}}"
        
        # 临时修改导出格式
        original_formats = refiner.exporter.formats
        refiner.exporter.formats = [format_type]
        
        try:
            exported = refiner.exporter.export(
                content=content,
                filename_template=filename_template,
                mode=mode
            )
            
            if format_type in exported:
                filepath = exported[format_type]
                # 返回相对路径，用于下载
                output_dir = refiner.config.get('output', {}).get('output_dir', './output')
                rel_path = os.path.relpath(filepath, output_dir)
                return jsonify({
                    'success': True,
                    'filepath': os.path.join(output_dir, rel_path),
                    'filename': os.path.basename(filepath)
                })
            else:
                return jsonify({'error': '导出失败'}), 500
        
        finally:
            refiner.exporter.formats = original_formats
    
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'initialized': refiner is not None
    })

if __name__ == '__main__':
    # 初始化系统
    config_path = os.getenv('CONFIG_PATH', None)
    if not init_refiner(config_path):
        print("警告: 系统初始化失败，请检查配置文件")
    
    # 启动服务器
    port = int(os.getenv('PORT', 8080))  # 默认使用 8080 端口，避免与 macOS AirPlay 冲突
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 启动 Web 服务器，访问 http://localhost:{port}")
    print(f"💡 提示: 如需更改端口，请设置环境变量 PORT=端口号")
    app.run(host='0.0.0.0', port=port, debug=debug)

