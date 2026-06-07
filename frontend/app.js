const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const clearFile = document.getElementById('clearFile');
const hintInput = document.getElementById('hintInput');
const submitBtn = document.getElementById('submitBtn');
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const resultSection = document.getElementById('resultSection');
const successCard = document.getElementById('successCard');
const errorCard = document.getElementById('errorCard');
const downloadLink = document.getElementById('downloadLink');
const errorText = document.getElementById('errorText');
const newTaskBtn = document.getElementById('newTaskBtn');
const retryBtn = document.getElementById('retryBtn');

let selectedFile = null;
let pollTimer = null;

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) selectFile(fileInput.files[0]);
});
clearFile.addEventListener('click', () => {
    selectedFile = null;
    fileInfo.hidden = true;
    uploadArea.hidden = false;
    submitBtn.disabled = true;
});
submitBtn.addEventListener('click', startProcessing);
newTaskBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

function selectFile(file) {
    selectedFile = file;
    fileName.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
    fileInfo.hidden = false;
    uploadArea.hidden = true;
    submitBtn.disabled = false;
}

async function startProcessing() {
    if (!selectedFile) return;

    submitBtn.disabled = true;
    uploadSection.querySelector('.form-group').hidden = true;
    progressSection.hidden = false;
    resultSection.hidden = true;

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (hintInput.value.trim()) {
        formData.append('hint', hintInput.value.trim());
    }

    try {
        progressText.textContent = '正在上传视频...';
        progressFill.style.width = '5%';

        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '上传失败');
        }

        const data = await resp.json();
        pollStatus(data.task_id);
    } catch (e) {
        showError(e.message);
    }
}

function pollStatus(taskId) {
    pollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/task/${taskId}`);
            const task = await resp.json();

            progressFill.style.width = task.progress + '%';
            progressPercent.textContent = task.progress + '%';
            progressText.textContent = task.message;

            if (task.status === 'completed') {
                clearInterval(pollTimer);
                showSuccess(taskId);
            } else if (task.status === 'failed') {
                clearInterval(pollTimer);
                showError(task.error || '处理失败');
            }
        } catch (e) {
            clearInterval(pollTimer);
            showError('连接服务器失败');
        }
    }, 2000);
}

function showSuccess(taskId) {
    progressSection.hidden = true;
    resultSection.hidden = false;
    successCard.hidden = false;
    errorCard.hidden = true;
    downloadLink.href = `/api/download/${taskId}`;
}

function showError(msg) {
    progressSection.hidden = true;
    resultSection.hidden = false;
    successCard.hidden = true;
    errorCard.hidden = false;
    errorText.textContent = msg;
}

function resetUI() {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.hidden = true;
    uploadArea.hidden = false;
    submitBtn.disabled = true;
    uploadSection.querySelector('.form-group').hidden = false;
    progressSection.hidden = true;
    resultSection.hidden = true;
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    hintInput.value = '';
}
