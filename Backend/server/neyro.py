import sys
import os
from pathlib import Path


from pdf_segmenter import process_pdf_to_txt
from gigachat import GigaChat

# Полные пути к файлам (замените на ваши реальные пути)
PDF_FILES = []

API_TOKEN = 'MDE5OTc1YzktMTIxZS03NTM1LWEzNDYtNTUyY2Y4ZTMzYzg2OjcwYWJmNTM2LTI0YWEtNGJhMi05N2ZiLWU3YzQzNTVmYWEzYw=='


class File:
    """Класс для представления файла в системе GigaChat"""

    def __init__(self, index: int, id: str, fullname: str):
        self.index = index
        self.id = id
        self.fullname = fullname

    def __repr__(self):
        return f"File(index={self.index}, id='{self.id}', fullname='{self.fullname}')"


class GigaChatManager:
    """Менеджер для работы с GigaChat API"""

    def __init__(self, api_token: str):
        self.giga = GigaChat(
            credentials=api_token,
            verify_ssl_certs=False,
        )
        self._files_cache = None

    def _get_files_data(self):
        """Получение данных о файлах с кэшированием"""
        if self._files_cache is None:
            self._files_cache = self.giga.get_files()
        return self._files_cache

    @property
    def files(self) -> list[File]:
        """Список всех файлов в системе"""
        return [
            File(index, data.id_, data.filename)
            for index, data in enumerate(self._get_files_data().data)
        ]

    def delete_all_files(self):
        """Удаление всех файлов"""
        print("🗑️  Начало удаления всех файлов из GigaChat...")
        files_count = len(self.files)
        for i, file in enumerate(self.files, 1):
            print(f"Удаление файла {i}/{files_count}: {file.fullname}")
            self.giga.delete_file(file.id)
        self._files_cache = None  # Сброс кэша
        print("✅ Все файлы удалены")

    def delete_file_by_id(self, file_id: str):
        """Удаление файла по ID"""
        self.giga.delete_file(file_id)
        self._files_cache = None  # Сброс кэша

    def upload_file(self, file_path: str | Path):
        """Загрузка файла"""
        file_path = Path(file_path)
        print(f"📤 Загрузка файла: {file_path.name}")
        
        with open(file_path, "rb") as file:
            self.giga.upload_file(file)
        self._files_cache = None  # Сброс кэша
        print(f"✅ Файл {file_path.name} успешно загружен")

    def get_files_in_dataset(self) -> list[str]:
        """Получение списка имен файлов в датасете"""
        return [file.fullname for file in self.files]

    def ask_according_to_material(self, message: str, material_id: str):
        """Запрос на основе документа (исправленная версия)"""
        # Создаем промпт с указанием контекста документов
        prompt = f"""Ты - эксперт в области инженерии и машиностроения. 
Ты в полной мере владеешь материалом и терминами, ты не пользуешься условными обозначениями, 
а используешь в своей речи наименования материалов или инструментала, с которым работаешь.

Отвечай на основе загруженных в тебя технических документов.

Вопрос: {message}

Ответь технически грамотно:"""

        result = self.giga.chat({
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "attachments": [material_id],
                }
            ],
            "temperature": 0.7
        })
        return result


def process_and_upload_pdf_files():
    """Обработка PDF файлов и загрузка в GigaChat"""
    giga_manager = GigaChatManager(API_TOKEN)
    
    print("🚀 Начало обработки PDF файлов и загрузки в GigaChat")
    print("=" * 60)
    
    # Очищаем все файлы перед началом
    giga_manager.delete_all_files()
    
    processed_files = []
    
    for pdf_path in PDF_FILES:
        file_path = Path(pdf_path)
        
        if not file_path.exists():
            print(f"❌ Файл не найден: {pdf_path}")
            continue
            
        print(f"\n📄 Обработка файла: {file_path.name}")
        print("-" * 40)
        
        try:
            # Обрабатываем PDF с помощью функции из pdf_segmenter
            processed_text = process_pdf_to_txt(str(file_path))
            
            # Сохраняем обработанный текст во временный файл
            temp_txt_path = file_path.with_suffix('.processed.txt')
            with open(temp_txt_path, 'w', encoding='utf-8') as f:
                f.write(processed_text)
            
            print(f"✅ PDF обработан, создан файл: {temp_txt_path.name}")
            
            # Загружаем обработанный файл в GigaChat
            giga_manager.upload_file(temp_txt_path)
            processed_files.append(temp_txt_path)
            
        except Exception as e:
            print(f"❌ Ошибка при обработке {file_path.name}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("📊 Итоги обработки:")
    print(f"✅ Успешно обработано: {len(processed_files)} файлов")
    print(f"📁 Всего файлов в GigaChat: {len(giga_manager.files)}")
    
    # Выводим список загруженных файлов
    if giga_manager.files:
        print("\n📋 Загруженные файлы:")
        for file in giga_manager.files:
            print(f"  - {file.fullname}")
    
    return giga_manager, processed_files


def ask_question_to_material(giga_manager: GigaChatManager, question: str, file_index: int = 0):
    """Задать вопрос по конкретному материалу"""
    files = giga_manager.files
    if not files:
        print("❌ Нет загруженных файлов")
        return None
    
    if file_index >= len(files):
        print(f"❌ Неверный индекс файла. Доступно файлов: {len(files)}")
        return None
    
    selected_file = files[file_index]
    print(f"📝 Вопрос по файлу: {selected_file.fullname}")
    print(f"❓ Вопрос: {question}")
    print("-" * 40)
    
    try:
        response = giga_manager.ask_according_to_material(question, selected_file.id)
        answer = response.choices[0].message.content
        print(f"🤖 Ответ:\n{answer}")
        print("-" * 40)
        return answer
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        return None