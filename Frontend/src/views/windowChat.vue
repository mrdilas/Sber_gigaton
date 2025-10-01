<!-- windowChat.vue - убедимся что все правильно -->
<template>
  <div class="container">
    <div class="history-container">
      <HistoryWindow
        @pdf-selected="onPdfSelected"
        @file-uploaded="onFileUploaded"
        ref="historyWindow"
      />
    </div>

    <div class="chat-container">
      <ChatWindow :selectedFileId="selectedFileId" ref="chatWindow"/>
    </div>

    <div class="button-container">
      <ButtonWindow ref="buttonWindow"/>
    </div>
  </div>
</template>

<script>
import ButtonWindow from '../components/buttonWindow.vue'
import ChatWindow from '../components/chatWindow.vue'
import HistoryWindow from '../components/historyWindow.vue'

export default {
  name: 'WindowChat',

  components: {
    ButtonWindow,
    ChatWindow,
    HistoryWindow,
  },

  data() {
    return {
      selectedFileId: null
    }
  },

  methods: {
    onPdfSelected(fileId) {
      console.log('Получен ID файла от HistoryWindow:', fileId);
      this.selectedFileId = fileId;
    },

    onFileUploaded(fileId) {
      console.log('Загружен новый файл с ID:', fileId);
      // Можно автоматически выбрать новый файл если нужно
      // this.selectedFileId = fileId;
    }
  },

  mounted() {
    console.log('WindowChat компонент монтирован');
  }
}
</script>

<style scoped>
.container {
  display: flex;
  width: 100%;
  height: 100vh; /* Используем viewport height */
}

.history-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  overflow-y: auto;
  width: 40vh;
  height: 100%;
  padding: 50px;
  box-sizing: border-box;
}

.chat-container {
  width: 120vh;
  height: 100%;
}

.button-container {
  width: 39vh;
  height: 100%;
}
</style>