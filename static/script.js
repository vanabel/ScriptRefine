// 全局变量
let currentFile = null;
let currentResults = {};

// DOM 元素
const textTab = document.getElementById('text-tab');
const uploadTab = document.getElementById('upload-tab');
const textInput = document.getElementById('input-text');
const fileInput = document.getElementById('file-input');
const fileUploadArea = document.getElementById('file-upload-area');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file');
const processBtn = document.getElementById('process-btn');
const processMode = document.getElementById('process-mode');
const outputSection = document.getElementById('output-section');
const outputTabs = document.getElementById('output-tabs');
const outputContent = document.getElementById('output-content');
const downloadSection = document.getElementById('download-section');
const downloadButtons = document.getElementById('download-buttons');
const clearBtn = document.getElementById('clear-btn');
const loadingOverlay = document.getElementById('loading-overlay');
const toast = document.getElementById('toast');
const charCount = document.getElementById('char-count');

// 标签页切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        
        // 更新按钮状态
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // 更新内容
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        if (tab === 'text') {
            textTab.classList.add('active');
        } else {
            uploadTab.classList.add('active');
        }
    });
});

// 字符计数
textInput.addEventListener('input', () => {
    charCount.textContent = textInput.value.length;
});

// 文件上传区域点击
fileUploadArea.addEventListener('click', (e) => {
    if (e.target !== fileInput && !fileInfo.contains(e.target)) {
        fileInput.click();
    }
});

// 文件选择
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        currentFile = file;
        fileName.textContent = file.name;
        fileInfo.style.display = 'flex';
        fileUploadArea.querySelector('.upload-placeholder').style.display = 'none';
    }
});

// 移除文件
removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    currentFile = null;
    fileInput.value = '';
    fileInfo.style.display = 'none';
    fileUploadArea.querySelector('.upload-placeholder').style.display = 'block';
});

// 拖拽上传
fileUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUploadArea.style.borderColor = '#2563eb';
});

fileUploadArea.addEventListener('dragleave', () => {
    fileUploadArea.style.borderColor = '';
});

fileUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUploadArea.style.borderColor = '';
    
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.txt') || file.name.endsWith('.md'))) {
        currentFile = file;
        fileInput.files = e.dataTransfer.files;
        fileName.textContent = file.name;
        fileInfo.style.display = 'flex';
        fileUploadArea.querySelector('.upload-placeholder').style.display = 'none';
    } else {
        showToast('请上传 .txt 或 .md 格式的文件', 'error');
    }
});

// 处理按钮
processBtn.addEventListener('click', async () => {
    const mode = processMode.value;
    
    // 验证输入
    if (textTab.classList.contains('active')) {
        const text = textInput.value.trim();
        if (!text) {
            showToast('请输入文本内容', 'error');
            return;
        }
        await processText(text, mode);
    } else {
        if (!currentFile) {
            showToast('请选择文件', 'error');
            return;
        }
        await processFile(currentFile, mode);
    }
});

// 处理文本
async function processText(text, mode) {
    showLoading(true);
    processBtn.disabled = true;
    
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                mode: mode
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentResults = data.results;
            displayResults(data.results, mode);
            showToast('处理完成！', 'success');
        } else {
            showToast(data.error || '处理失败', 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    } finally {
        showLoading(false);
        processBtn.disabled = false;
    }
}

// 处理文件
async function processFile(file, mode) {
    showLoading(true);
    processBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentResults = data.results;
            displayResults(data.results, mode, data.downloads);
            showToast('处理完成！', 'success');
        } else {
            showToast(data.error || '处理失败', 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    } finally {
        showLoading(false);
        processBtn.disabled = false;
    }
}

// 显示结果
function displayResults(results, mode, downloads = {}) {
    outputSection.style.display = 'block';
    
    // 清空之前的内容
    outputTabs.innerHTML = '';
    outputContent.innerHTML = '';
    downloadButtons.innerHTML = '';
    
    // 创建标签页
    if (results.full) {
        const btn = document.createElement('button');
        btn.className = 'output-tab-btn active';
        btn.textContent = '完整版';
        btn.onclick = () => showOutput('full', results.full);
        outputTabs.appendChild(btn);
    }
    
    if (results.summary) {
        const btn = document.createElement('button');
        btn.className = 'output-tab-btn';
        btn.textContent = '会议纪要';
        btn.onclick = () => showOutput('summary', results.summary);
        outputTabs.appendChild(btn);
    }
    
    // 显示第一个结果
    if (results.full) {
        showOutput('full', results.full);
    } else if (results.summary) {
        showOutput('summary', results.summary);
    }
    
    // 创建下载按钮
    if (results.full || results.summary) {
        const content = results.full || results.summary;
        
        // Word 下载
        const wordBtn = document.createElement('button');
        wordBtn.className = 'btn btn-download';
        wordBtn.textContent = '📄 下载 Word';
        wordBtn.onclick = () => exportFile(content, 'docx', mode);
        downloadButtons.appendChild(wordBtn);
        
        // PDF 下载
        const pdfBtn = document.createElement('button');
        pdfBtn.className = 'btn btn-download';
        pdfBtn.textContent = '📕 下载 PDF';
        pdfBtn.onclick = () => exportFile(content, 'pdf', mode);
        downloadButtons.appendChild(pdfBtn);
        
        // Markdown 下载
        const mdBtn = document.createElement('button');
        mdBtn.className = 'btn btn-download';
        mdBtn.textContent = '📝 下载 Markdown';
        mdBtn.onclick = () => exportFile(content, 'markdown', mode);
        downloadButtons.appendChild(mdBtn);
    }
}

// 显示输出内容
function showOutput(type, content) {
    // 更新标签页状态
    document.querySelectorAll('.output-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if ((type === 'full' && btn.textContent === '完整版') ||
            (type === 'summary' && btn.textContent === '会议纪要')) {
            btn.classList.add('active');
        }
    });
    
    // 显示内容
    outputContent.textContent = content;
}

// 导出文件
async function exportFile(content, format, mode) {
    showLoading(true);
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: content,
                format: format,
                mode: mode
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 下载文件
            const filepath = encodeURIComponent(data.filepath);
            window.location.href = `/api/download?path=${filepath}`;
            showToast('文件导出成功！', 'success');
        } else {
            showToast(data.error || '导出失败', 'error');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 清空按钮
clearBtn.addEventListener('click', () => {
    outputSection.style.display = 'none';
    currentResults = {};
    textInput.value = '';
    charCount.textContent = '0';
    if (currentFile) {
        removeFileBtn.click();
    }
});

// 显示/隐藏加载提示
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
    if (show) {
        processBtn.querySelector('.btn-text').style.display = 'none';
        processBtn.querySelector('.btn-loading').style.display = 'inline';
    } else {
        processBtn.querySelector('.btn-text').style.display = 'inline';
        processBtn.querySelector('.btn-loading').style.display = 'none';
    }
}

// 显示提示消息
function showToast(message, type = 'error') {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 页面加载时检查健康状态
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        if (!data.initialized) {
            showToast('系统未初始化，请检查配置', 'error');
        }
    } catch (error) {
        console.error('健康检查失败:', error);
    }
});

