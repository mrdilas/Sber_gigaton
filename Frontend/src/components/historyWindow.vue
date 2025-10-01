<!-- historyWindow.vue - исправленная версия -->
<template>
  <div class="history-window">
    <!-- Кнопка загрузки PDF -->
    <button 
      class="button-pdf upload-btn"
      type="button"
      @click="triggerFileUpload"
      :disabled="isLoading"
    >
      <img :src="cloudIcon" alt="Добавление файла" class="cloud-icon"/>
      {{ isLoading ? 'Загрузка...' : 'Загрузить PDF' }}
    </button>
    
    <!-- Скрытый input для загрузки файлов -->
    <input 
      type="file" 
      ref="fileInput"
      @change="handleFileUpload"
      accept=".pdf"
      style="display: none"
    />

    <!-- Список PDF файлов из Supabase -->
    <div class="pdf-list" v-if="pdfFiles.length > 0">
      <div 
        v-for="pdf in pdfFiles"
        :key="pdf.id"
        class="pdf-item"
        :class="{ active: activePdfId === pdf.id }"
      >
        <button 
          class="button-pdf pdf-btn"
          type="button"
          @click="selectPdfFile(pdf.id)"
        >
          <img :src="pdfIcon" alt="PDF файл" class="pdf-icon"/>
          <span class="pdf-name">{{ pdf.name }}</span>
        </button>
        <button 
          class="delete-btn"
          @click="deletePdfFile(pdf)"
          title="Удалить файл"
          :disabled="isLoading"
        >
          ×
        </button>
      </div>
    </div>

    <!-- Сообщение если файлов нет -->
    <div v-else class="no-files">
      Нет загруженных файлов
    </div>

    <!-- Индикатор загрузки -->
    <div v-if="isLoading" class="loading-indicator">
      Загрузка...
    </div>
  </div>
</template>

<script>
import cloudIcon from '../assets/cloud.svg';
import pdfIcon from '../assets/pdf.svg';

export default {
  name: 'HistoryWindow',

  data() {
    return {
      cloudIcon: cloudIcon,
      pdfIcon: pdfIcon,
      activePdfId: null,
      pdfFiles: [],
      isLoading: false
    }
  },

  async mounted() {
    await this.loadPdfFiles();
  },

  methods: {
    triggerFileUpload() {
      if (this.isLoading) return;
      this.$refs.fileInput.click();
    },

    selectPdfFile(pdfId) {
      if (this.isLoading) return;
      this.activePdfId = pdfId;
      this.$emit('pdf-selected', pdfId);
      console.log('Передаем ID файла:', pdfId);
    },

    async handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file || this.isLoading) return;

      // Валидация файла
      if (file.type !== 'application/pdf') {
        alert('Пожалуйста, выберите PDF файл');
        return;
      }

      const maxSize = 150 * 1024 * 1024;
      if (file.size > maxSize) {
        alert('Файл слишком большой. Максимальный размер 150MB');
        return;
      }

      this.isLoading = true;

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:5000/api/pdf/upload', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        await this.loadPdfFiles();
        event.target.value = '';
        
        if (data.file && data.file.id) {
          this.$emit('file-uploaded', data.file.id);
        }
        
        alert(`Файл успешно загружен! Размер: ${data.file_size_mb || (file.size / (1024 * 1024)).toFixed(2)} MB`);

      } catch (error) {
        console.error('Ошибка загрузки файла:', error);
        alert('Ошибка при загрузке файла: ' + error.message);
      } finally {
        this.isLoading = false;
      }
    },

    async loadPdfFiles() {
      try {
        const response = await fetch('http://localhost:5000/api/pdf/files');
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error);
        
        this.pdfFiles = data.files.map(file => ({
          id: file.id,
          name: file.name,
          url: file.file_url,
          storage_path: file.storage_path,
          uploaded_at: file.uploaded_at
        }));

        console.log('Загружен список файлов:', this.pdfFiles);

      } catch (error) {
        console.error('Ошибка загрузки списка файлов:', error);
        this.pdfFiles = [];
      }
    },

    async deletePdfFile(pdf) {
      if (!confirm(`Удалить файл "${pdf.name}"?`) || this.isLoading) return;

      try {
        const response = await fetch(`http://localhost:5000/api/pdf/delete/${pdf.id}`, {
          method: 'DELETE'
        });

        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error);

        await this.loadPdfFiles();

        if (this.activePdfId === pdf.id) {
          this.activePdfId = null;
          this.$emit('pdf-selected', null);
        }

      } catch (error) {
        console.error('Ошибка удаления файла:', error);
        alert('Ошибка при удалении файла: ' + error.message);
      }
    }
  }
}
</script>

<style scoped>
.history-window {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  width: 100%;
}

.pdf-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  align-items: center;
}

.pdf-item {
  position: relative;
  width: 300px;
  display: flex;
  align-items: center;
}

.pdf-item.active .button-pdf {
  background: rgb(142, 241, 142);
  border-color: #1e7c29;
  color: #2d2d2d;
}

.button-pdf {
  width: 300px;
  height: 50px;
  border-radius: 8px;
  padding: 0 15px;
  background: white;
  border: 2px solid #2aa835;
  color: rgb(77, 76, 76);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

.button-pdf:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pdf-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}

.delete-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  opacity: 0;
  transition: all 0.3s ease;
  z-index: 10;
}

.delete-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pdf-item:hover .delete-btn:not(:disabled) {
  opacity: 1;
}

.delete-btn:hover:not(:disabled) {
  background: #cc0000;
  transform: translateY(-50%) scale(1.1);
}

.button-pdf:hover:not(.active):not(:disabled) {
  transform: translateY(-2px);
  background: rgba(142, 241, 142, 0.3);
}

.pdf-item.active .button-pdf:hover:not(:disabled) {
  transform: translateY(-2px);
  background: rgb(120, 220, 120);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.button-pdf:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.cloud-icon,
.pdf-icon {
  width: 30px;
  height: 30px;
  object-fit: contain;
  flex-shrink: 0;
}

.loading-indicator {
  color: #666;
  font-style: italic;
}

.no-files {
  color: #666;
  font-style: italic;
  text-align: center;
  padding: 20px;
}
</style>