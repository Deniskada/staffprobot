/**
 * JavaScript для загрузки медиа-файлов в системе отзывов.
 * Поддерживает drag&drop, предпросмотр и валидацию файлов.
 */

class MediaUploader {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }
        
        this.options = {
            maxFiles: options.maxFiles || 10,
            allowedTypes: options.allowedTypes || ['photo', 'video', 'audio', 'document'],
            reviewId: options.reviewId || null,
            onUploadComplete: options.onUploadComplete || null,
            onError: options.onError || null,
            ...options
        };
        
        this.files = [];
        this.uploadProgress = {};
        this.isUploading = false;
        
        this.init();
    }
    
    init() {
        this.createHTML();
        this.bindEvents();
        this.loadUploadLimits();
    }
    
    createHTML() {
        this.container.innerHTML = `
            <div class="media-upload-area" id="media-upload-area">
                <div class="upload-dropzone">
                    <div class="upload-icon">
                        <i class="fas fa-cloud-upload-alt"></i>
                    </div>
                    <div class="upload-text">
                        <p>Перетащите файлы сюда или <span class="upload-link">выберите файлы</span></p>
                        <small class="upload-limits">Загружайте фото, видео, аудио или документы</small>
                    </div>
                    <input type="file" id="media-file-input" multiple accept="image/*,video/*,audio/*,.pdf,.doc,.docx" style="display: none;">
                </div>
                <div class="upload-progress" id="upload-progress" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <div class="progress-text" id="progress-text">0%</div>
                </div>
            </div>
            <div class="media-preview" id="media-preview"></div>
            <div class="media-errors" id="media-errors" style="display: none;"></div>
        `;
        
        this.dropzone = this.container.querySelector('.upload-dropzone');
        this.fileInput = this.container.querySelector('#media-file-input');
        this.progressContainer = this.container.querySelector('#upload-progress');
        this.progressFill = this.container.querySelector('#progress-fill');
        this.progressText = this.container.querySelector('#progress-text');
        this.previewContainer = this.container.querySelector('#media-preview');
        this.errorsContainer = this.container.querySelector('#media-errors');
    }
    
    bindEvents() {
        // Drag & Drop события
        this.dropzone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropzone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropzone.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Клик по области загрузки
        this.dropzone.addEventListener('click', () => this.fileInput.click());
        
        // Выбор файлов через input
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Клик по ссылке "выберите файлы"
        const uploadLink = this.container.querySelector('.upload-link');
        uploadLink.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropzone.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }
    
    async processFiles(files) {
        if (this.isUploading) {
            this.showError('Загрузка уже выполняется');
            return;
        }
        
        if (files.length === 0) {
            return;
        }
        
        // Проверяем количество файлов
        if (this.files.length + files.length > this.options.maxFiles) {
            this.showError(`Максимальное количество файлов: ${this.options.maxFiles}`);
            return;
        }
        
        // Валидируем файлы
        const validationResult = await this.validateFiles(files);
        
        if (validationResult.invalidFiles.length > 0) {
            const errors = validationResult.invalidFiles.map(f => f.error).join('<br>');
            this.showError(errors);
        }
        
        if (validationResult.validFiles.length === 0) {
            return;
        }
        
        // Добавляем валидные файлы
        this.files.push(...validationResult.validFiles);
        
        // Обновляем предпросмотр
        this.updatePreview();
        
        // Очищаем input
        this.fileInput.value = '';
    }
    
    async validateFiles(files) {
        try {
            const formData = new FormData();
            files.forEach(file => formData.append('files', file));
            
            const response = await fetch('/api/media/validate', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Ошибка валидации файлов');
            }
            
            return {
                validFiles: files.filter((file, index) => result.results[index].valid),
                invalidFiles: result.results.filter(r => !r.valid)
            };
            
        } catch (error) {
            console.error('Validation error:', error);
            this.showError('Ошибка валидации файлов');
            return { validFiles: [], invalidFiles: [] };
        }
    }
    
    updatePreview() {
        this.previewContainer.innerHTML = '';
        
        this.files.forEach((file, index) => {
            const previewItem = this.createPreviewItem(file, index);
            this.previewContainer.appendChild(previewItem);
        });
    }
    
    createPreviewItem(file, index) {
        const item = document.createElement('div');
        item.className = 'media-preview-item';
        item.dataset.index = index;
        
        const fileType = this.getFileType(file.type);
        const fileSize = this.formatFileSize(file.size);
        
        item.innerHTML = `
            <div class="preview-content">
                <div class="preview-icon">
                    ${this.getFileIcon(fileType)}
                </div>
                <div class="preview-info">
                    <div class="preview-name">${file.name}</div>
                    <div class="preview-details">${fileType.toUpperCase()} • ${fileSize}</div>
                </div>
                <div class="preview-actions">
                    <button type="button" class="btn-remove" onclick="mediaUploader.removeFile(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        return item;
    }
    
    getFileType(mimeType) {
        if (mimeType.startsWith('image/')) return 'photo';
        if (mimeType.startsWith('video/')) return 'video';
        if (mimeType.startsWith('audio/')) return 'audio';
        return 'document';
    }
    
    getFileIcon(fileType) {
        const icons = {
            photo: '<i class="fas fa-image"></i>',
            video: '<i class="fas fa-video"></i>',
            audio: '<i class="fas fa-music"></i>',
            document: '<i class="fas fa-file"></i>'
        };
        return icons[fileType] || '<i class="fas fa-file"></i>';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    removeFile(index) {
        this.files.splice(index, 1);
        this.updatePreview();
    }
    
    async uploadFiles() {
        if (this.files.length === 0) {
            this.showError('Нет файлов для загрузки');
            return;
        }
        
        if (!this.options.reviewId) {
            this.showError('ID отзыва не указан');
            return;
        }
        
        this.isUploading = true;
        this.showProgress();
        
        try {
            const formData = new FormData();
            formData.append('review_id', this.options.reviewId);
            
            this.files.forEach((file, index) => {
                formData.append('files', file);
                this.uploadProgress[index] = 0;
            });
            
            const response = await fetch('/api/media/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Ошибка загрузки файлов');
            }
            
            // Успешная загрузка
            this.files = [];
            this.updatePreview();
            this.hideProgress();
            
            if (this.options.onUploadComplete) {
                this.options.onUploadComplete(result.media);
            }
            
            this.showSuccess(`Загружено ${result.media.length} файлов`);
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Ошибка загрузки файлов: ' + error.message);
        } finally {
            this.isUploading = false;
            this.hideProgress();
        }
    }
    
    showProgress() {
        this.progressContainer.style.display = 'block';
        this.updateProgress(0);
    }
    
    hideProgress() {
        this.progressContainer.style.display = 'none';
    }
    
    updateProgress(percent) {
        this.progressFill.style.width = percent + '%';
        this.progressText.textContent = Math.round(percent) + '%';
    }
    
    showError(message) {
        this.errorsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                ${message}
            </div>
        `;
        this.errorsContainer.style.display = 'block';
        
        setTimeout(() => {
            this.errorsContainer.style.display = 'none';
        }, 5000);
    }
    
    showSuccess(message) {
        this.errorsContainer.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                ${message}
            </div>
        `;
        this.errorsContainer.style.display = 'block';
        
        setTimeout(() => {
            this.errorsContainer.style.display = 'none';
        }, 3000);
    }
    
    async loadUploadLimits() {
        try {
            const response = await fetch('/api/media/limits');
            const result = await response.json();
            
            if (result.success) {
                this.uploadLimits = result.limits;
                this.updateLimitsDisplay();
            }
        } catch (error) {
            console.error('Error loading upload limits:', error);
        }
    }
    
    updateLimitsDisplay() {
        const limitsText = this.container.querySelector('.upload-limits');
        if (limitsText && this.uploadLimits) {
            const photoLimit = this.uploadLimits.photo.max_size_mb;
            const videoLimit = this.uploadLimits.video.max_size_mb;
            const audioLimit = this.uploadLimits.audio.max_size_mb;
            const docLimit = this.uploadLimits.document.max_size_mb;
            
            limitsText.textContent = `Фото до ${photoLimit}MB, видео до ${videoLimit}MB, аудио до ${audioLimit}MB, документы до ${docLimit}MB`;
        }
    }
    
    clear() {
        this.files = [];
        this.updatePreview();
        this.hideProgress();
        this.errorsContainer.style.display = 'none';
    }
    
    getFiles() {
        return this.files;
    }
    
    setFiles(files) {
        this.files = files;
        this.updatePreview();
    }
}

// Глобальная переменная для доступа к загрузчику
let mediaUploader = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('media-upload-container');
    if (uploadContainer) {
        const reviewId = uploadContainer.dataset.reviewId;
        mediaUploader = new MediaUploader('media-upload-container', {
            reviewId: reviewId,
            maxFiles: 10,
            onUploadComplete: function(media) {
                console.log('Upload complete:', media);
                // Здесь можно обновить интерфейс отзыва
            },
            onError: function(error) {
                console.error('Upload error:', error);
            }
        });
    }
});
